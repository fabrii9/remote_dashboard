import { Component, proxy, onWillStart, onMounted, onWillUnmount, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

export class RemoteDashboard extends Component {
    static template = "remote_dashboard.Dashboard";
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = proxy({
            loading: true,
            syncing: false,
            configured: false,
            dashboardName: "",
            remoteUrl: "",
            lastSync: false,
            currentTime: "",
            visibleColumns: [],
            columns: {},
            expandedCards: {},
            refreshCountdown: 15,
            zoomLevel: 100,
            zplLabelMode: "none",
            hasZplPrinter: false,
            hasRicohPrinter: false,
        });

        this._refreshInterval = null;
        this._clockInterval = null;
        this._countdownInterval = null;
        this.REFRESH_SECONDS = 15;

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
        });

        onWillUnmount(() => {
            if (this._refreshInterval) clearInterval(this._refreshInterval);
            if (this._clockInterval) clearInterval(this._clockInterval);
            if (this._countdownInterval) clearInterval(this._countdownInterval);
        });
    }

    async loadDashboard() {
        try {
            const data = await this.orm.call("remote.odoo.config", "get_dashboard_data", [this.configId]);

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
                this.state.hasRicohPrinter = data.has_ricoh_printer || false;
                this.state.soFontSize = data.so_font_size || 0;
            }
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
            await this.orm.call("remote.odoo.config", "action_sync_pickings", [this.configId]);
            await this.loadDashboard();
            this.notification.add("Sincronización completada", { type: "success" });
        } catch (e) {
            this.notification.add("Error al sincronizar: " + this._errorMessage(e), { type: "danger" });
        }
        this.state.syncing = false;
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
            await this.orm.call("remote.odoo.config", "validate_remote_picking", [this.configId, remoteId]);
            this.notification.add("Picking validado correctamente", { type: "success" });
            await this.loadDashboard();
        } catch (e) {
            this.notification.add("Error al validar: " + this._errorMessage(e), { type: "danger" });
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

    async onPrintRicoh(ev, remoteId) {
        ev.stopPropagation();
        if (!confirm("¿Enviar el PDF de este picking a la impresora Ricoh?")) return;
        try {
            await this.orm.call("remote.odoo.config", "print_picking_ricoh", [this.configId, remoteId]);
            this.notification.add("PDF enviado a la impresora", { type: "success" });
        } catch (e) {
            this.notification.add("Error al imprimir: " + this._errorMessage(e), { type: "danger" });
        }
    }

    async onPrintZPLLabel(ev, remoteId) {
        ev.stopPropagation();
        if (!confirm("¿Imprimir etiqueta ZPL?")) return;
        try {
            await this.orm.call("remote.odoo.config", "print_zpl_label", [this.configId, remoteId]);
            this.notification.add("Etiqueta enviada a la impresora", { type: "success" });
        } catch (e) {
            this.notification.add("Error al imprimir ZPL: " + this._errorMessage(e), { type: "danger" });
        }
    }

    async onViewZPLLabel(ev, remoteId) {
        ev.stopPropagation();
        try {
            const url = await this.orm.call("remote.odoo.config", "view_zpl_label", [this.configId, remoteId]);
            if (url) {
                window.open(url, "_blank");
            }
        } catch (e) {
            this.notification.add("Error al generar ZPL: " + this._errorMessage(e), { type: "danger" });
        }
    }

    _errorMessage(e) {
        return e?.data?.message || e?.message || e;
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

registry.category("actions").add("remote_dashboard.dashboard", RemoteDashboard);
