/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart, onMounted, onWillUnmount } = owl;

export class RemoteDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            syncing: false,
            configured: false,
            dashboardName: "",
            remoteUrl: "",
            lastSync: false,
            currentTime: "",
            visibleColumns: [],
            columns: {},
            kpis: null,
            expandedCards: {},
            refreshCountdown: 15,
            zoomLevel: 100,
            zplLabelMode: "none",
            hasZplPrinter: false,
        });

        this._refreshInterval = null;
        this._clockInterval = null;
        this._countdownInterval = null;
        this._syncInterval = null;
        this.REFRESH_SECONDS = 15;
        this.SYNC_SECONDS = 15;

        const params = this.props.action?.params || {};
        this.configId = params.config_id || false;

        onWillStart(async () => {
            await this.loadDashboard();
        });

        onMounted(() => {
            this._refreshInterval = setInterval(() => this.loadDashboard(), this.REFRESH_SECONDS * 1000);
            this._updateClock();
            this._clockInterval = setInterval(() => this._updateClock(), 1000);
            this.state.refreshCountdown = this.REFRESH_SECONDS;
            this._countdownInterval = setInterval(() => {
                if (this.state.refreshCountdown > 0) {
                    this.state.refreshCountdown--;
                }
            }, 1000);
            // Auto-sync from remote every SYNC_SECONDS
            this._syncInterval = setInterval(() => this._autoSync(), this.SYNC_SECONDS * 1000);
            // Also trigger first sync shortly after mount
            setTimeout(() => this._autoSync(), 3000);
        });

        onWillUnmount(() => {
            if (this._refreshInterval) clearInterval(this._refreshInterval);
            if (this._clockInterval) clearInterval(this._clockInterval);
            if (this._countdownInterval) clearInterval(this._countdownInterval);
            if (this._syncInterval) clearInterval(this._syncInterval);
        });
    }

    async loadDashboard() {
        try {
            const [data, kpis] = await Promise.all([
                this.rpc("/web/dataset/call_kw", {
                    model: "remote.odoo.config",
                    method: "get_dashboard_data",
                    args: [this.configId],
                    kwargs: {},
                }),
                this.rpc("/web/dataset/call_kw", {
                    model: "remote.odoo.config",
                    method: "get_dashboard_kpis",
                    args: [this.configId],
                    kwargs: {},
                }),
            ]);

            this.state.configured = data.configured;
            if (data.configured) {
                this.state.dashboardName = data.dashboard_name || "Dashboard";
                this.state.remoteUrl = data.remote_url || "";
                this.state.lastSync = data.last_sync || false;
                this.state.visibleColumns = data.visible_columns || [];
                this.state.columns = data.columns || {};
                this.configId = data.config_id;
                this.state.zplLabelMode = data.zpl_label_mode || "none";
                this.state.hasZplPrinter = data.has_zpl_printer || false;
            }
            this.state.kpis = kpis || null;
        } catch (e) {
            console.error("Dashboard load error:", e);
        }
        this.state.loading = false;
        this.state.refreshCountdown = this.REFRESH_SECONDS;
    }

    async onRefresh() {
        this.state.loading = true;
        await this.loadDashboard();
    }

    async onSyncRemote() {
        this.state.syncing = true;
        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "remote.odoo.config",
                method: "action_sync_pickings",
                args: [this.configId],
                kwargs: {},
            });
            await this.loadDashboard();
            this.notification.add("Sincronización completada", { type: "success" });
        } catch (e) {
            this.notification.add("Error al sincronizar: " + (e.message || e), { type: "danger" });
        }
        this.state.syncing = false;
    }

    async _autoSync() {
        // Silent background sync — no toasts, no loading spinners
        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "remote.odoo.config",
                method: "action_sync_pickings",
                args: [this.configId],
                kwargs: {},
            });
            await this.loadDashboard();
        } catch (e) {
            console.warn("Auto-sync error:", e);
        }
    }

    getColumnLabel(colKey) {
        const col = this.state.columns[colKey];
        return col ? col.label : colKey;
    }

    getColumnItems(colKey) {
        const col = this.state.columns[colKey];
        return col ? col.items : [];
    }

    toggleCard(remoteId) {
        this.state.expandedCards[remoteId] = !this.state.expandedCards[remoteId];
    }

    openRemotePicking(ev, remoteId) {
        ev.stopPropagation();
        if (this.state.remoteUrl && remoteId) {
            window.open(
                `${this.state.remoteUrl}/web#id=${remoteId}&model=stock.picking&view_type=form`,
                "_blank"
            );
        }
    }

    openRemoteSaleOrder(ev, soId) {
        ev.stopPropagation();
        if (this.state.remoteUrl && soId) {
            window.open(
                `${this.state.remoteUrl}/web#id=${soId}&model=sale.order&view_type=form`,
                "_blank"
            );
        }
    }

    async onValidatePicking(ev, remoteId) {
        ev.stopPropagation();
        if (!confirm("¿Confirmar validación del picking?")) return;
        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "remote.odoo.config",
                method: "validate_remote_picking",
                args: [this.configId, remoteId],
                kwargs: {},
            });
            this.notification.add("Picking validado correctamente", { type: "success" });
            await this.loadDashboard();
        } catch (e) {
            this.notification.add("Error al validar: " + (e.message || e), { type: "danger" });
        }
    }

    onPrintPicking(ev, remoteId) {
        ev.stopPropagation();
        if (this.state.remoteUrl && remoteId) {
            window.open(
                `${this.state.remoteUrl}/report/pdf/stock.report_picking/${remoteId}`,
                "_blank"
            );
        }
    }

    async onPrintZPLLabel(ev, remoteId) {
        ev.stopPropagation();
        if (!confirm("¿Imprimir etiqueta ZPL?")) return;
        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "remote.odoo.config",
                method: "print_zpl_label",
                args: [this.configId, remoteId],
                kwargs: {},
            });
            this.notification.add("Etiqueta enviada a la impresora", { type: "success" });
        } catch (e) {
            this.notification.add("Error al imprimir ZPL: " + (e.message || e), { type: "danger" });
        }
    }

    async onViewZPLLabel(ev, remoteId) {
        ev.stopPropagation();
        try {
            const url = await this.rpc("/web/dataset/call_kw", {
                model: "remote.odoo.config",
                method: "view_zpl_label",
                args: [this.configId, remoteId],
                kwargs: {},
            });
            if (url) {
                window.open(url, "_blank");
            }
        } catch (e) {
            this.notification.add("Error al generar ZPL: " + (e.message || e), { type: "danger" });
        }
    }

    _updateClock() {
        const now = new Date();
        this.state.currentTime = now.toLocaleTimeString("es-AR", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    formatDate(dt) {
        if (!dt) return "";
        try {
            const d = new Date(dt);
            return d.toLocaleDateString("es-AR", {
                day: "2-digit",
                month: "2-digit",
                year: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch {
            return dt;
        }
    }

    onZoomIn() {
        this.state.zoomLevel = Math.min(this.state.zoomLevel + 10, 200);
    }

    onZoomOut() {
        this.state.zoomLevel = Math.max(this.state.zoomLevel - 10, 60);
    }

    onZoomReset() {
        this.state.zoomLevel = 100;
    }

    formatWaiting(minutes) {
        if (!minutes || minutes <= 0) return "";
        if (minutes < 60) return `${minutes} min`;
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return m > 0 ? `${h}h ${m}m` : `${h}h`;
    }
}

RemoteDashboard.template = "remote_dashboard.Dashboard";

registry.category("actions").add("remote_dashboard.dashboard", RemoteDashboard);
