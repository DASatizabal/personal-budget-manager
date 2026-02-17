"""Bank API integration view — Plaid-powered balance sync."""

import logging
from datetime import datetime
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QProgressBar, QSplitter, QTextEdit,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QToolButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ..models.account import Account
from ..models.credit_card import CreditCard
from ..models.loan import Loan
from ..models.plaid_link import PlaidItem, PlaidAccountMapping
from ..utils import plaid_config

_logger = logging.getLogger('budget_app.bank_api_view')


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class LinkWorker(QThread):
    """Runs the Plaid Link browser flow in a background thread."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, link_token: str):
        super().__init__()
        self.link_token = link_token

    def run(self):
        try:
            from ..utils.plaid_link_server import run_plaid_link
            result = run_plaid_link(self.link_token)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SyncWorker(QThread):
    """Fetches balances + recent transactions for all linked items."""
    progress = pyqtSignal(int, int, str)  # current, total, institution_name
    finished = pyqtSignal(list, list)      # balances_per_mapping, all_transactions
    error = pyqtSignal(str)

    def __init__(self, items: List[PlaidItem]):
        super().__init__()
        self.items = items

    def run(self):
        from ..utils.plaid_client import get_balances, sync_transactions, PlaidClientError

        all_balance_rows = []   # (PlaidAccountMapping, PlaidAccountBalance)
        all_transactions = []

        total = len(self.items)
        for idx, item in enumerate(self.items):
            self.progress.emit(idx, total, item.institution_name or "Unknown")
            try:
                balances = get_balances(item.access_token)
                mappings = item.load_mappings()
                bal_by_id = {b.account_id: b for b in balances}

                for mapping in mappings:
                    if not mapping.is_synced:
                        continue
                    bal = bal_by_id.get(mapping.plaid_account_id)
                    if bal:
                        all_balance_rows.append((mapping, bal))

                # Fetch recent transactions
                try:
                    result = sync_transactions(item.access_token, item.transaction_cursor)
                    all_transactions.extend(result.added)
                    # Save cursor for next incremental sync
                    item.transaction_cursor = result.next_cursor
                    item.last_sync = datetime.now().isoformat()
                    item.save()
                except PlaidClientError:
                    pass  # Balance sync succeeded; transaction sync is best-effort

            except PlaidClientError as e:
                _logger.warning("Sync failed for %s: %s", item.institution_name, e)

        self.progress.emit(total, total, "Done")
        self.finished.emit(all_balance_rows, all_transactions)


# ---------------------------------------------------------------------------
# Account Mapping Dialog
# ---------------------------------------------------------------------------

class AccountMappingDialog(QDialog):
    """Maps each Plaid account to a local account / credit card / loan."""

    def __init__(self, parent, mappings: List[PlaidAccountMapping]):
        super().__init__(parent)
        self.setWindowTitle("Map Plaid Accounts")
        self.setMinimumWidth(650)
        self.mappings = mappings
        self._combos: list = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Map each Plaid account to its corresponding local account, credit card, or loan.\n"
            "Leave as '(unmapped)' to skip syncing that account."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        # Build choices: (display_text, local_type, local_id)
        choices = [("(unmapped)", None, None)]
        for a in Account.get_all():
            choices.append((f"Account: {a.name}", "account", a.id))
        for c in CreditCard.get_all():
            choices.append((f"Credit Card: {c.name}", "credit_card", c.id))
        for l in Loan.get_all():
            choices.append((f"Loan: {l.name}", "loan", l.id))

        for mapping in self.mappings:
            label_parts = [mapping.plaid_account_name or ""]
            if mapping.plaid_account_mask:
                label_parts.append(f"(•••{mapping.plaid_account_mask})")
            if mapping.plaid_account_type:
                label_parts.append(f"[{mapping.plaid_account_type}]")
            label = " ".join(label_parts)

            combo = QComboBox()
            for display, lt, lid in choices:
                combo.addItem(display, (lt, lid))

            # Pre-select if already mapped or auto-mapped
            if mapping.local_type and mapping.local_id:
                for i, (_, lt, lid) in enumerate(choices):
                    if lt == mapping.local_type and lid == mapping.local_id:
                        combo.setCurrentIndex(i)
                        break

            form.addRow(label, combo)
            self._combos.append(combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_updated_mappings(self) -> List[PlaidAccountMapping]:
        """Return mappings with local_type/local_id set from combo selections."""
        for mapping, combo in zip(self.mappings, self._combos):
            local_type, local_id = combo.currentData()
            mapping.local_type = local_type
            mapping.local_id = local_id
        return self.mappings


# ---------------------------------------------------------------------------
# Main View
# ---------------------------------------------------------------------------

class BankAPIView(QWidget):
    """Plaid-powered bank balance sync view."""

    def __init__(self):
        super().__init__()
        self._link_worker: Optional[LinkWorker] = None
        self._sync_worker: Optional[SyncWorker] = None
        self._balance_rows: list = []  # cached (mapping, plaid_balance) tuples
        self._setup_ui()

    # ── UI setup ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Settings (collapsible) ────────────────────────────────────────
        self._settings_group = QGroupBox("Plaid API Settings")
        self._settings_group.setCheckable(True)
        self._settings_group.setChecked(False)
        settings_layout = QFormLayout(self._settings_group)

        self._client_id_edit = QLineEdit()
        self._client_id_edit.setPlaceholderText("Plaid client_id")
        settings_layout.addRow("Client ID:", self._client_id_edit)

        self._secret_edit = QLineEdit()
        self._secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret_edit.setPlaceholderText("Plaid secret")
        settings_layout.addRow("Secret:", self._secret_edit)

        self._env_combo = QComboBox()
        self._env_combo.addItems(["sandbox", "development", "production"])
        settings_layout.addRow("Environment:", self._env_combo)

        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self._save_settings)
        settings_layout.addRow("", save_settings_btn)

        root.addWidget(self._settings_group)

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self._link_btn = QPushButton("Link New Account")
        self._link_btn.clicked.connect(self._start_link_flow)
        toolbar.addWidget(self._link_btn)

        self._sync_btn = QPushButton("Sync All Balances")
        self._sync_btn.setStyleSheet("QPushButton { background-color: #2e7d32; }")
        self._sync_btn.clicked.connect(self._start_sync)
        toolbar.addWidget(self._sync_btn)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        toolbar.addWidget(self._progress, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_items_table)
        toolbar.addWidget(refresh_btn)

        root.addLayout(toolbar)

        # ── Linked Institutions table ─────────────────────────────────────
        items_group = QGroupBox("Linked Institutions")
        items_layout = QVBoxLayout(items_group)

        self._items_table = QTableWidget()
        self._items_table.setColumnCount(6)
        self._items_table.setHorizontalHeaderLabels([
            "Institution", "Accounts", "Last Sync", "Status", "Map", "Remove"
        ])
        hdr = self._items_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        items_layout.addWidget(self._items_table)
        root.addWidget(items_group)

        # ── Sync Results (splitter) ───────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Balance changes table
        balance_widget = QWidget()
        balance_layout = QVBoxLayout(balance_widget)
        balance_layout.setContentsMargins(0, 0, 0, 0)
        balance_layout.addWidget(QLabel("Balance Changes"))

        self._balance_table = QTableWidget()
        self._balance_table.setColumnCount(6)
        self._balance_table.setHorizontalHeaderLabels([
            "Account", "Plaid Balance", "Local Balance", "Change", "Status", "Apply"
        ])
        bhdr = self._balance_table.horizontalHeader()
        bhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3, 4, 5):
            bhdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        balance_layout.addWidget(self._balance_table)

        self._apply_all_btn = QPushButton("Apply All Balance Updates")
        self._apply_all_btn.setStyleSheet("QPushButton { background-color: #1565c0; }")
        self._apply_all_btn.setEnabled(False)
        self._apply_all_btn.clicked.connect(self._apply_all_balances)
        balance_layout.addWidget(self._apply_all_btn)

        splitter.addWidget(balance_widget)

        # Recent transactions (read-only)
        txn_widget = QWidget()
        txn_layout = QVBoxLayout(txn_widget)
        txn_layout.setContentsMargins(0, 0, 0, 0)
        txn_layout.addWidget(QLabel("Recent Transactions"))

        self._txn_text = QTextEdit()
        self._txn_text.setReadOnly(True)
        self._txn_text.setFont(QFont("Consolas", 9))
        txn_layout.addWidget(self._txn_text)

        splitter.addWidget(txn_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, 1)

        # Load saved settings into UI
        self._load_settings()
        self._update_button_states()

    # ── Settings persistence ──────────────────────────────────────────────

    def _load_settings(self):
        cfg = plaid_config.load_config()
        self._client_id_edit.setText(cfg.get("client_id", ""))
        self._secret_edit.setText(cfg.get("secret", ""))
        env = cfg.get("environment", "sandbox")
        idx = self._env_combo.findText(env)
        if idx >= 0:
            self._env_combo.setCurrentIndex(idx)

    def _save_settings(self):
        plaid_config.save_config({
            "client_id": self._client_id_edit.text().strip(),
            "secret": self._secret_edit.text().strip(),
            "environment": self._env_combo.currentText(),
        })
        self._update_button_states()
        QMessageBox.information(self, "Settings", "Plaid credentials saved.")

    def _update_button_states(self):
        configured = plaid_config.is_configured()
        self._link_btn.setEnabled(configured)
        self._sync_btn.setEnabled(configured and bool(PlaidItem.get_all()))
        if not configured:
            self._link_btn.setToolTip("Configure Plaid credentials first (expand Settings)")
            self._sync_btn.setToolTip("Configure Plaid credentials first")
        else:
            self._link_btn.setToolTip("")
            self._sync_btn.setToolTip("")

    # ── Refresh ───────────────────────────────────────────────────────────

    def refresh(self):
        self._refresh_items_table()
        self._update_button_states()

    def _refresh_items_table(self):
        items = PlaidItem.get_all()
        self._items_table.setRowCount(len(items))

        for row, item in enumerate(items):
            mappings = item.load_mappings()
            acct_names = ", ".join(
                f"{m.plaid_account_name} (•••{m.plaid_account_mask})"
                if m.plaid_account_mask else (m.plaid_account_name or "?")
                for m in mappings
            ) or "—"

            last_sync = "Never"
            if item.last_sync:
                try:
                    dt = datetime.fromisoformat(item.last_sync)
                    last_sync = dt.strftime("%m/%d/%Y %I:%M %p")
                except ValueError:
                    last_sync = item.last_sync

            self._items_table.setItem(row, 0, QTableWidgetItem(item.institution_name or "Unknown"))
            self._items_table.setItem(row, 1, QTableWidgetItem(acct_names))
            self._items_table.setItem(row, 2, QTableWidgetItem(last_sync))
            self._items_table.setItem(row, 3, QTableWidgetItem(item.status))

            map_btn = QPushButton("Map")
            map_btn.clicked.connect(lambda checked, i=item: self._open_mapping_dialog(i))
            self._items_table.setCellWidget(row, 4, map_btn)

            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("QPushButton { color: #f44336; }")
            remove_btn.clicked.connect(lambda checked, i=item: self._remove_item(i))
            self._items_table.setCellWidget(row, 5, remove_btn)

        self._update_button_states()

    # ── Link flow ─────────────────────────────────────────────────────────

    def _start_link_flow(self):
        if self._link_worker and self._link_worker.isRunning():
            QMessageBox.warning(self, "Busy", "A link flow is already in progress.")
            return

        self._link_btn.setEnabled(False)
        self._link_btn.setText("Linking…")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate

        try:
            from ..utils.plaid_client import create_link_token, PlaidClientError
            link_token = create_link_token()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create link token:\n{e}")
            self._link_btn.setEnabled(True)
            self._link_btn.setText("Link New Account")
            self._progress.setVisible(False)
            return

        self._link_worker = LinkWorker(link_token)
        self._link_worker.finished.connect(self._on_link_finished)
        self._link_worker.error.connect(self._on_link_error)
        self._link_worker.start()

    def _on_link_finished(self, result: dict):
        self._link_btn.setEnabled(True)
        self._link_btn.setText("Link New Account")
        self._progress.setVisible(False)

        if "error" in result:
            QMessageBox.warning(self, "Link Failed", str(result["error"]))
            return
        if result.get("cancelled"):
            return

        public_token = result.get("public_token")
        if not public_token:
            QMessageBox.warning(self, "Link Failed", "No public token received.")
            return

        # Exchange token
        try:
            from ..utils.plaid_client import exchange_public_token, get_balances
            access_token, item_id = exchange_public_token(public_token)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Token exchange failed:\n{e}")
            return

        # Extract institution info from metadata
        metadata = result.get("metadata", {})
        institution = metadata.get("institution", {})
        inst_name = institution.get("name", "Unknown")
        inst_id = institution.get("institution_id", "")

        # Save PlaidItem
        plaid_item = PlaidItem(
            id=None,
            item_id=item_id,
            access_token=access_token,
            institution_name=inst_name,
            institution_id=inst_id,
        )
        plaid_item.save()

        # Fetch accounts and create mappings
        try:
            balances = get_balances(access_token)
        except Exception as e:
            QMessageBox.warning(
                self, "Warning",
                f"Institution linked but failed to fetch accounts:\n{e}"
            )
            self._refresh_items_table()
            return

        mappings = []
        for bal in balances:
            mapping = PlaidAccountMapping(
                id=None,
                plaid_item_id=plaid_item.id,
                plaid_account_id=bal.account_id,
                plaid_account_name=bal.name,
                plaid_account_official_name=bal.official_name,
                plaid_account_type=bal.type,
                plaid_account_subtype=bal.subtype,
                plaid_account_mask=bal.mask,
            )
            # Auto-map by heuristic
            self._auto_map_account(mapping)
            mapping.save()
            mappings.append(mapping)

        # Show mapping dialog
        self._refresh_items_table()
        dialog = AccountMappingDialog(self, mappings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for m in dialog.get_updated_mappings():
                m.save()
            self._refresh_items_table()

    def _on_link_error(self, message: str):
        self._link_btn.setEnabled(True)
        self._link_btn.setText("Link New Account")
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Link Error", message)

    # ── Auto-mapping heuristic ────────────────────────────────────────────

    def _auto_map_account(self, mapping: PlaidAccountMapping):
        """Try to match a Plaid account to a local account by mask, name, or type."""
        mask = mapping.plaid_account_mask
        pname = (mapping.plaid_account_name or "").lower()
        ptype = (mapping.plaid_account_type or "").lower()

        candidates = []

        if ptype in ("depository",):
            candidates = [
                ("account", a.id, a.name, a.pay_type_code)
                for a in Account.get_all()
            ]
        elif ptype == "credit":
            candidates = [
                ("credit_card", c.id, c.name, c.pay_type_code)
                for c in CreditCard.get_all()
            ]
        elif ptype == "loan":
            candidates = [
                ("loan", l.id, l.name, l.pay_type_code)
                for l in Loan.get_all()
            ]

        if not candidates:
            return

        # 1. Match by last-4 digits
        if mask:
            for local_type, local_id, name, code in candidates:
                if code and code.endswith(mask):
                    mapping.local_type = local_type
                    mapping.local_id = local_id
                    return
                # Also try matching the mask against last 4 of name
                if mask in name:
                    mapping.local_type = local_type
                    mapping.local_id = local_id
                    return

        # 2. Match by name similarity (substring)
        for local_type, local_id, name, code in candidates:
            if pname and (pname in name.lower() or name.lower() in pname):
                mapping.local_type = local_type
                mapping.local_id = local_id
                return

        # 3. If only one candidate of the right type, use it
        if len(candidates) == 1:
            local_type, local_id, _, _ = candidates[0]
            mapping.local_type = local_type
            mapping.local_id = local_id

    # ── Mapping dialog ────────────────────────────────────────────────────

    def _open_mapping_dialog(self, item: PlaidItem):
        mappings = item.load_mappings()
        if not mappings:
            QMessageBox.information(self, "No Accounts", "This institution has no accounts to map.")
            return
        dialog = AccountMappingDialog(self, mappings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for m in dialog.get_updated_mappings():
                m.save()
            self._refresh_items_table()

    def _remove_item(self, item: PlaidItem):
        reply = QMessageBox.question(
            self, "Remove Institution",
            f"Remove {item.institution_name} and all its account mappings?\n\n"
            "This does not revoke access at the bank — you can re-link anytime.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            item.delete()
            self._refresh_items_table()

    # ── Sync flow ─────────────────────────────────────────────────────────

    def _start_sync(self):
        if self._sync_worker and self._sync_worker.isRunning():
            QMessageBox.warning(self, "Busy", "A sync is already in progress.")
            return

        items = PlaidItem.get_all()
        if not items:
            QMessageBox.information(self, "No Accounts", "Link a bank account first.")
            return

        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("Syncing…")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(items))
        self._progress.setValue(0)

        self._sync_worker = SyncWorker(items)
        self._sync_worker.progress.connect(self._on_sync_progress)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_progress(self, current: int, total: int, name: str):
        self._progress.setValue(current)
        self._progress.setFormat(f"Syncing {name}… ({current}/{total})")

    def _on_sync_finished(self, balance_rows: list, transactions: list):
        self._sync_btn.setEnabled(True)
        self._sync_btn.setText("Sync All Balances")
        self._progress.setVisible(False)

        self._balance_rows = balance_rows
        self._populate_balance_table(balance_rows)
        self._populate_transactions(transactions)
        self._refresh_items_table()

    def _on_sync_error(self, message: str):
        self._sync_btn.setEnabled(True)
        self._sync_btn.setText("Sync All Balances")
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Sync Error", message)

    # ── Balance results table ─────────────────────────────────────────────

    def _populate_balance_table(self, balance_rows: list):
        self._balance_table.setRowCount(len(balance_rows))
        has_changes = False

        for row, (mapping, plaid_bal) in enumerate(balance_rows):
            local_name = mapping.get_local_display_name()
            local_balance = self._get_local_balance(mapping)
            plaid_balance = plaid_bal.current
            change = plaid_balance - local_balance

            self._balance_table.setItem(row, 0, QTableWidgetItem(local_name))

            plaid_item = QTableWidgetItem(f"${plaid_balance:,.2f}")
            plaid_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._balance_table.setItem(row, 1, plaid_item)

            local_item = QTableWidgetItem(f"${local_balance:,.2f}")
            local_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._balance_table.setItem(row, 2, local_item)

            change_item = QTableWidgetItem(f"${change:+,.2f}")
            change_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if abs(change) > 0.005:
                change_item.setForeground(
                    Qt.GlobalColor.green if change > 0 else Qt.GlobalColor.red
                )
            self._balance_table.setItem(row, 3, change_item)

            status = "Match" if abs(change) < 0.01 else "Different"
            self._balance_table.setItem(row, 4, QTableWidgetItem(status))

            apply_btn = QPushButton("Apply")
            apply_btn.setEnabled(abs(change) >= 0.01 and mapping.local_type is not None)
            apply_btn.clicked.connect(
                lambda checked, r=row: self._apply_single_balance(r)
            )
            self._balance_table.setCellWidget(row, 5, apply_btn)

            if abs(change) >= 0.01 and mapping.local_type is not None:
                has_changes = True

        self._apply_all_btn.setEnabled(has_changes)

    def _get_local_balance(self, mapping: PlaidAccountMapping) -> float:
        if mapping.local_type == "account" and mapping.local_id:
            obj = Account.get_by_id(mapping.local_id)
            return obj.current_balance if obj else 0.0
        elif mapping.local_type == "credit_card" and mapping.local_id:
            obj = CreditCard.get_by_id(mapping.local_id)
            return obj.current_balance if obj else 0.0
        elif mapping.local_type == "loan" and mapping.local_id:
            obj = Loan.get_by_id(mapping.local_id)
            return obj.current_balance if obj else 0.0
        return 0.0

    def _apply_single_balance(self, row: int):
        if row >= len(self._balance_rows):
            return
        mapping, plaid_bal = self._balance_rows[row]
        self._update_local_balance(mapping, plaid_bal.current)

        # Refresh the row
        local_balance = plaid_bal.current
        self._balance_table.item(row, 2).setText(f"${local_balance:,.2f}")
        self._balance_table.item(row, 3).setText(f"$+0.00")
        self._balance_table.item(row, 4).setText("Match")
        btn = self._balance_table.cellWidget(row, 5)
        if btn:
            btn.setEnabled(False)

        # Check if any changes remain
        self._check_remaining_changes()

    def _apply_all_balances(self):
        count = 0
        for row, (mapping, plaid_bal) in enumerate(self._balance_rows):
            if mapping.local_type is None:
                continue
            local_balance = self._get_local_balance(mapping)
            if abs(plaid_bal.current - local_balance) >= 0.01:
                self._update_local_balance(mapping, plaid_bal.current)
                count += 1

        if count:
            QMessageBox.information(
                self, "Balances Updated",
                f"Updated {count} balance(s).\n\n"
                "Switch to Dashboard or Credit Cards tab to see updated values."
            )
            # Refresh balance table to show matches
            self._populate_balance_table(self._balance_rows)

    def _update_local_balance(self, mapping: PlaidAccountMapping, new_balance: float):
        if mapping.local_type == "account" and mapping.local_id:
            obj = Account.get_by_id(mapping.local_id)
            if obj:
                obj.current_balance = new_balance
                obj.save()
        elif mapping.local_type == "credit_card" and mapping.local_id:
            obj = CreditCard.get_by_id(mapping.local_id)
            if obj:
                obj.current_balance = new_balance
                obj.save()
        elif mapping.local_type == "loan" and mapping.local_id:
            obj = Loan.get_by_id(mapping.local_id)
            if obj:
                obj.current_balance = new_balance
                obj.save()

    def _check_remaining_changes(self):
        has_changes = False
        for mapping, plaid_bal in self._balance_rows:
            if mapping.local_type is None:
                continue
            local_balance = self._get_local_balance(mapping)
            if abs(plaid_bal.current - local_balance) >= 0.01:
                has_changes = True
                break
        self._apply_all_btn.setEnabled(has_changes)

    # ── Transaction display ───────────────────────────────────────────────

    def _populate_transactions(self, transactions: list):
        if not transactions:
            self._txn_text.setPlainText("No recent transactions found.")
            return

        lines = []
        # Sort by date descending
        transactions.sort(key=lambda t: t.date, reverse=True)
        for txn in transactions[:100]:  # cap at 100
            # Negate amount for display: Plaid positive = debit
            display_amt = -txn.amount
            sign = "+" if display_amt >= 0 else "-"
            lines.append(
                f"{txn.date}  {sign}${abs(display_amt):>9,.2f}  {txn.name}"
            )
            if txn.category:
                lines.append(f"           {txn.category}")
            if txn.pending:
                lines.append(f"           (pending)")

        self._txn_text.setPlainText("\n".join(lines))
