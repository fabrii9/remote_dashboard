import xmlrpc.client
import ssl
import time
import random
import logging
import ast

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

STATE_LABELS = {
    'draft': 'Borrador',
    'waiting': 'En espera',
    'confirmed': 'Esperando',
    'assigned': 'Disponible',
    'done': 'Hecho',
    'cancel': 'Cancelado',
}

BUNDLE_MAP = {
    "TFR0070": 5, "TFR0072": 5, "TFR0076": 5, "TFR0075": 5,
    "TFR0071": 4, "TFR0091": 3, "TFR0079": 5, "TFR0074": 5,
    "TFR0078": 5, "TFR0077": 5, "TFR0073": 4, "TFR0091N": 3,
    "TFR0089": 3, "TFR0084": 3, "TFR0088": 3, "TFR0087": 3,
    "TFR0083": 3, "TFR0092": 2, "TFR0080": 3, "TFR0082": 3,
    "TFR0086": 3, "TFR0085": 3, "TFR0081": 3, "TFR0090": 2,
    "TFRTP33B": 3, "TFRTP34B": 3, "TFRTP35B": 2, "TFRTP36B": 2,
    "TFRTP37B": 2, "TFRTP33N": 3, "TFRTP34N": 3, "TFRTP35N": 2,
    "TFRTP36N": 2, "TFRTP37N": 2,
    "TRO614026B": 3, "TRO614026N": 3, "TRO61406B": 3, "TRO41406N": 3,
    "TRO01302": 3, "TRO01302N": 3, "TRO01301": 3, "TRO01301N": 3,
    "TRO01311": 10, "TRO01311N": 10, "TRO01310": 10, "TRO01310N": 10,
    "TCT00015": 3, "TCT00015N": 3, "TCT00020": 3, "TCT00020N": 3,
    "TCT00030": 3, "TCT00030N": 3, "TCT0001": 3, "TCT0001N": 3,
    "TCT0002": 3, "TCT0002N": 3, "TCT0003": 3, "TCT0003N": 3,
    "TCT0004": 2, "TCT0004N": 2,
    "TRO01103": 5, "TRO01103N": 5, "TRO01102": 5, "TRO01102N": 5,
    "TRO01101": 5, "TRO01101N": 5,
    "TRO1081N": 15, "TRO1081": 15, "TRO06182": 15,
    "TRO01073": 15, "TRO01073N": 15, "TRO01072": 15, "TRO01072N": 15,
    "TRO01071": 15, "TRO01071N": 15, "TRO01071SP": 15,
    "TRO01722": 15, "TRO01722N": 15, "TRO01724": 15, "TRO01724N": 15,
    "TRO01726AN": 15, "TRO01726": 15, "TRO01726N": 15,
    "6197B3": 10, "6197B": 10, "6197N3": 10, "6197N": 10,
    "6198B3": 10, "6198B": 10, "6198N3": 10, "6198N": 10,
    "TRO01039": 10, "TRO01038": 10, "TRO01037": 10,
    "TRO01039M": 10, "TRO01038M": 10, "TRO01037M": 10,
    "TRO01037N": 10, "TRO01039N": 10, "TRO01038N": 10,
    "TTU0251": 15, "TTU0252": 15, "TTU0254": 15,
    "TTU0012R": 3, "TTU0013R": 3, "TTU00114": 3, "TTU0011": 3,
    "TTU00028R2": 15, "TTU0009": 10, "TTU0007D": 10,
    "TTU00028R4": 15, "TTU0008": 10, "TTU0006D": 10,
    "TTU00028R": 15, "TTU0002": 10, "TTU0005D": 10,
    "TTU0102": 8, "TTU0101": 10, "TTU0103": 3,
    "CTR003": 20, "CTR004": 20, "CTR002": 20, "CTR001": 20,
    "CTRN001": 20, "CTR005": 20,
    "8402": 10, "8405": 10,
    "TTU0051": 4, "TTU0053": 4, "TTU0054": 4,
    "TTU0055": 3, "TTU0056": 3, "TTU0057": 2,
    "TTU0052": 4, "TTU0060": 2, "TTU0061": 2, "TTU0062": 2,
    "BVB01": 5, "BV05": 5, "TTU0153": 4, "TTU0154": 4,
    "TTU0151": 2, "TTU0150": 4, "TTU0149": 4, "TTU0152": 2, "TTU0104": 3,
}

CATEGORY_IDS = [
    125, 198, 183, 223, 224, 210, 209, 202, 203, 204, 205, 218, 206, 207,
    180, 156, 225, 157, 214, 174, 217, 212, 213, 211, 149, 150, 244, 245,
    243, 246, 242, 176, 175, 148, 177, 178, 222, 221, 136, 109, 124, 123,
    134, 208,
]


class RemoteOdooConfig(models.Model):
    _name = 'remote.odoo.config'
    _description = 'Configuración de Dashboard Remoto'
    _rec_name = 'name'

    name = fields.Char(
        string='Nombre del Dashboard',
        required=True,
        default='Mi Dashboard',
    )
    url = fields.Char(
        string='URL',
        required=True,
        default='https://train-printemps-11-02-2.adhoc.ar/',
        help='URL del servidor Odoo remoto (incluir https://)',
    )
    database = fields.Char(
        string='Base de datos',
        required=True,
        default='train-printemps-11-02-2',
    )
    username = fields.Char(string='Usuario', required=True)
    password = fields.Char(string='Contraseña / API Key', required=True)
    remote_uid = fields.Integer(string='UID Remoto', readonly=True, copy=False)
    last_sync = fields.Datetime(string='Última sincronización', readonly=True, copy=False)

    # ---- Columnas visibles ----
    show_en_preparacion = fields.Boolean(
        string='Mostrar "En Preparación"',
        default=False,
    )
    show_despachar = fields.Boolean(
        string='Mostrar "Despachar"',
        default=False,
    )
    show_mostrador_preparacion = fields.Boolean(
        string='Mostrar "Mostrador – En Preparación"',
        default=True,
    )
    show_mostrador_despachar = fields.Boolean(
        string='Mostrar "Mostrador – Listo para Entregar"',
        default=True,
    )

    # ---- IDs de Tipos de Operación ----
    preparacion_picking_type_ids = fields.Char(
        string='IDs Tipo Op. Preparación',
        default='',
        help='IDs separados por coma. Dejar vacío si no se usa.',
    )
    despachar_picking_type_ids = fields.Char(
        string='IDs Tipo Op. Despachar',
        default='',
        help='IDs separados por coma. Dejar vacío si no se usa.',
    )
    mostrador_picking_type_ids = fields.Char(
        string='IDs Tipo Op. Mostrador (OUT)',
        default='233',
        help='IDs del tipo de operación de salida (entregas) del Mostrador.',
    )
    mostrador_prep_picking_type_ids = fields.Char(
        string='IDs Tipo Op. Preparación Mostrador',
        default='',
        help='IDs de operaciones internas para Mostrador. '
             'Cuando todos estén hechos, el OUT pasa a "Listo para Entregar".',
    )

    # ---- Filtro por estados ----
    mostrador_prep_states = fields.Char(
        string='Estados col. Preparación',
        default='',
        help='Estados a mostrar en la columna "En Preparación" separados por coma '
             '(ej: assigned, confirmed). Vacío = todos excepto done/cancel.',
    )
    mostrador_despachar_states = fields.Char(
        string='Estados col. Despachar',
        default='',
        help='Estados a mostrar en "Listo para Entregar" separados por coma '
             '(ej: assigned). Vacío = todos excepto done/cancel.',
    )
    available_states = fields.Text(
        string='Estados disponibles',
        readonly=True,
        help='Estados encontrados en el remoto (cargados con el botón).',
    )

    # ---- Filtro x_Tipo_Pedido ----
    x_tipo_pedido_filter = fields.Char(
        string='Tipo de Pedido',
        default='',
        help='Valores de x_Tipo_Pedido separados por coma (ej: Mostrador, Mostrador Retira). '
             'Vacío = sin filtro por tipo de pedido.',
    )
    available_tipo_pedido = fields.Text(
        string='Tipos de Pedido disponibles',
        readonly=True,
        help='Valores de x_Tipo_Pedido encontrados en el remoto.',
    )

    # ---- Filtro remoto ----
    remote_filter_id = fields.Integer(
        string='ID Filtro Remoto',
        default=0,
        help='ID de ir.filters en el Odoo remoto. 0 = sin filtro.',
    )

    # ---- Agrupación ----
    group_preparacion = fields.Boolean(string='Agrupar En Preparación', default=False)
    group_despachar = fields.Boolean(string='Agrupar Despachar', default=False)
    group_mostrador = fields.Boolean(string='Agrupar Mostrador', default=False)

    # ---- Opciones ----
    sync_interval = fields.Integer(
        string='Intervalo de sincronización (min)',
        default=5,
    )
    verify_ssl = fields.Boolean(string='Verificar SSL', default=True)
    max_retries = fields.Integer(string='Reintentos máximos', default=5)

    # ---- Etiquetas ZPL ----
    zpl_label_mode = fields.Selection(
        [
            ('none', 'Deshabilitado'),
            ('simple', 'Etiqueta simple (1 por línea)'),
            ('bundle_map', 'Etiqueta por bultos (BUNDLE_MAP)'),
        ],
        string='Modo etiqueta ZPL',
        default='none',
    )
    zpl_printer_url = fields.Char(
        string='URL Impresora ZPL',
        help='URL del endpoint /remote_zpl/print '
             '(ej: https://odoo.printemps.com.ar/remote_zpl/print)',
    )
    zpl_printer_token = fields.Char(
        string='Token Impresora ZPL',
    )
    zpl_logo = fields.Text(
        string='Logo ZPL',
        help='Código GFA del logo para incluir en la etiqueta (^FO...^GFA,...^FS)',
    )

    # ---- Impresora PDF Ricoh (RAW TCP) ----
    enable_ricoh_print = fields.Boolean(
        string='Habilitar impresión por red (Ricoh)',
        default=False,
        help='Cuando está activo, permite enviar el PDF del picking directamente '
             'a la impresora Ricoh por socket TCP RAW.',
    )
    ricoh_host = fields.Char(
        string='Host / IP de la impresora',
        help='Nombre de host o IP pública de la impresora (ej: aa890aa70c96.sn.mynetname.net).',
    )
    ricoh_port = fields.Integer(
        string='Puerto TCP',
        default=4000,
        help='Puerto RAW de la impresora (generalmente 9100 en red local, '
             'o el puerto público configurado en el router).',
    )
    ricoh_timeout = fields.Float(
        string='Timeout (seg)',
        default=10.0,
        help='Tiempo máximo de espera para la conexión TCP.',
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_ids(text):
        return [
            int(x.strip()) for x in (text or '').split(',')
            if x.strip().isdigit()
        ]

    @staticmethod
    def _parse_states(text):
        """Parsea string de estados separados por coma."""
        return [
            x.strip() for x in (text or '').split(',')
            if x.strip()
        ]

    def _get_ssl_context(self):
        self.ensure_one()
        if self.verify_ssl:
            return ssl.create_default_context()
        return ssl._create_unverified_context()

    def _execute_with_backoff(self, func, *args, max_retries=None, base_delay=1.0):
        retries = max_retries or self.max_retries or 5
        for attempt in range(retries):
            try:
                return func(*args)
            except xmlrpc.client.Fault:
                raise
            except Exception as e:
                if attempt == retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                _logger.warning(
                    "Remote API call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, retries, delay, str(e),
                )
                time.sleep(delay)

    def _authenticate(self):
        self.ensure_one()
        url = self.url.rstrip('/')
        ctx = self._get_ssl_context()
        common = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/common', context=ctx, allow_none=True,
        )
        uid = self._execute_with_backoff(
            common.authenticate, self.database, self.username, self.password, {},
        )
        if not uid:
            raise UserError(_('Autenticación fallida. Verifique las credenciales.'))
        self.sudo().write({'remote_uid': uid})
        return uid

    def _execute_kw(self, model, method, args=None, kwargs=None):
        self.ensure_one()
        if not self.remote_uid:
            self._authenticate()

        url = self.url.rstrip('/')
        ctx = self._get_ssl_context()
        proxy = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/object', context=ctx, allow_none=True,
        )

        try:
            return self._execute_with_backoff(
                proxy.execute_kw,
                self.database, self.remote_uid, self.password,
                model, method,
                args or [],
                kwargs or {},
            )
        except xmlrpc.client.Fault as e:
            if 'AccessDenied' in str(e) or 'access' in str(e).lower():
                self._authenticate()
                return self._execute_with_backoff(
                    proxy.execute_kw,
                    self.database, self.remote_uid, self.password,
                    model, method,
                    args or [],
                    kwargs or {},
                )
            raise

    @staticmethod
    def _strip_product_ref(name):
        """Remove [REF] prefix and leading * from product display name."""
        import re
        cleaned = re.sub(r'^\[.*?\]\s*', '', name or '')
        cleaned = cleaned.lstrip('*').strip()
        return cleaned

    @staticmethod
    def _clean_partner_name(name):
        """Return only the commercial partner name (strip address part after comma)."""
        if not name:
            return ''
        return name.split(',')[0].strip()

    def _get_remote_filter_domain(self):
        self.ensure_one()
        if not self.remote_filter_id:
            return []
        try:
            fdata = self._execute_kw(
                'ir.filters', 'read',
                args=[[self.remote_filter_id]],
                kwargs={'fields': ['domain']},
            )
            if fdata and fdata[0].get('domain'):
                domain = ast.literal_eval(fdata[0]['domain'])
                return domain if isinstance(domain, list) else []
        except Exception:
            _logger.warning("No se pudo cargar el filtro remoto ID=%s", self.remote_filter_id)
        return []

    # -------------------------------------------------------------------------
    # Acciones públicas
    # -------------------------------------------------------------------------

    def test_connection(self):
        self.ensure_one()
        try:
            uid = self._authenticate()
        except Exception as e:
            raise UserError(_('Error de conexión: %s') % str(e))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conexión exitosa'),
                'message': _('Conectado — UID remoto: %s') % uid,
                'type': 'success',
                'sticky': False,
            },
        }

    def test_ricoh_connection(self):
        """Prueba la conexión TCP RAW a la impresora Ricoh."""
        import socket
        self.ensure_one()
        if not self.ricoh_host or not self.ricoh_port:
            raise UserError(_('Configure el host y el puerto de la impresora primero.'))
        try:
            with socket.create_connection(
                (self.ricoh_host, int(self.ricoh_port)),
                timeout=float(self.ricoh_timeout or 10.0),
            ):
                pass
        except Exception as e:
            raise UserError(
                _('No se pudo conectar a %s:%s — %s') % (
                    self.ricoh_host, self.ricoh_port, str(e)
                )
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Impresora alcanzable'),
                'message': _('Conexión TCP a %s:%s establecida correctamente.') % (
                    self.ricoh_host, self.ricoh_port,
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_manual_sync(self):
        self.ensure_one()
        self.sync_pickings()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización completada'),
                'message': _('Los datos se han actualizado.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'remote_dashboard.dashboard',
            'name': self.name,
            'params': {'config_id': self.id},
        }

    def action_fetch_states(self):
        """Consulta los estados únicos de stock.picking en el Odoo remoto."""
        self.ensure_one()
        if not self.remote_uid:
            self._authenticate()
        most_ids = self._parse_ids(self.mostrador_picking_type_ids)
        most_prep_ids = self._parse_ids(self.mostrador_prep_picking_type_ids)
        all_type_ids = most_ids + most_prep_ids

        try:
            # Buscar estados distintos
            pickings = self._execute_kw(
                'stock.picking', 'search_read',
                args=[[('picking_type_id', 'in', all_type_ids)]],
                kwargs={'fields': ['state'], 'limit': 2000},
            ) or []
            states = sorted(set(p['state'] for p in pickings if p.get('state')))
            labels = [f"{s} ({STATE_LABELS.get(s, s)})" for s in states]
            self.sudo().write({
                'available_states': ', '.join(labels) if labels else 'No se encontraron estados',
            })
        except Exception as e:
            raise UserError(_('Error al obtener estados: %s') % str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Estados obtenidos'),
                'message': _('Se encontraron %d estados distintos.') % len(states),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_fetch_tipo_pedido(self):
        """Consulta los valores únicos de x_Tipo_Pedido en stock.picking del remoto."""
        self.ensure_one()
        if not self.remote_uid:
            self._authenticate()
        most_ids = self._parse_ids(self.mostrador_picking_type_ids)
        most_prep_ids = self._parse_ids(self.mostrador_prep_picking_type_ids)
        all_type_ids = most_ids + most_prep_ids

        try:
            domain = [('picking_type_id', 'in', all_type_ids)] if all_type_ids else []
            pickings = self._execute_kw(
                'stock.picking', 'search_read',
                args=[domain],
                kwargs={'fields': ['x_Tipo_Pedido'], 'limit': 3000},
            ) or []
            valores = sorted(set(
                p['x_Tipo_Pedido']
                for p in pickings
                if p.get('x_Tipo_Pedido')
            ))
            self.sudo().write({
                'available_tipo_pedido': ', '.join(valores) if valores else 'No se encontraron valores',
            })
        except Exception as e:
            raise UserError(_('Error al obtener x_Tipo_Pedido: %s') % str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tipos de Pedido obtenidos'),
                'message': _('Se encontraron %d valores distintos: %s') % (
                    len(valores), ', '.join(valores) if valores else '(ninguno)'
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    # -------------------------------------------------------------------------
    # Sincronización de pickings
    # -------------------------------------------------------------------------

    def sync_pickings(self):
        """Descarga pickings del Odoo remoto y actualiza la caché local."""
        self.ensure_one()
        Picking = self.env['remote.odoo.picking'].sudo()
        MoveLine = self.env['remote.odoo.move.line'].sudo()
        remote_fields = [
            'name', 'partner_id', 'scheduled_date', 'state',
            'origin', 'picking_type_id', 'x_Tipo_Pedido', 'create_date',
        ]
        has_state_detail = True

        prep_ids = self._parse_ids(self.preparacion_picking_type_ids)
        desp_ids = self._parse_ids(self.despachar_picking_type_ids)
        most_ids = self._parse_ids(self.mostrador_picking_type_ids)
        most_prep_ids = self._parse_ids(self.mostrador_prep_picking_type_ids)

        # Estados filtrados
        prep_states = self._parse_states(self.mostrador_prep_states)
        desp_states = self._parse_states(self.mostrador_despachar_states)

        filter_domain = self._get_remote_filter_domain()

        # Filtro x_Tipo_Pedido (soporta múltiples valores separados por coma)
        tipo_pedido_raw = (self.x_tipo_pedido_filter or '').strip()
        if tipo_pedido_raw:
            tipos = [t.strip() for t in tipo_pedido_raw.split(',') if t.strip()]
            if len(tipos) == 1:
                filter_domain = filter_domain + [('x_Tipo_Pedido', '=', tipos[0])]
            elif tipos:
                filter_domain = filter_domain + [('x_Tipo_Pedido', 'in', tipos)]

        en_prep = []
        despachar = []
        mostrador_preparacion = []
        mostrador_despachar = []

        try:
            # 1) En Preparación (general)
            if prep_ids:
                en_prep = self._execute_kw(
                    'stock.picking', 'search_read',
                    args=[[
                        ('picking_type_id', 'in', prep_ids),
                        ('state', 'not in', ['done', 'cancel']),
                    ] + filter_domain],
                    kwargs={'fields': remote_fields, 'limit': 500},
                ) or []

            # 2) Despachar (general)
            if desp_ids:
                despachar_candidates = self._execute_kw(
                    'stock.picking', 'search_read',
                    args=[[
                        ('picking_type_id', 'in', desp_ids),
                        ('state', '=', 'assigned'),
                    ] + filter_domain],
                    kwargs={'fields': remote_fields + ['group_id'], 'limit': 500},
                ) or []

                if despachar_candidates:
                    group_ids = list({
                        p['group_id'][0]
                        for p in despachar_candidates
                        if p.get('group_id')
                    })
                    candidate_ids = {p['id'] for p in despachar_candidates}

                    if group_ids:
                        pending_siblings = self._execute_kw(
                            'stock.picking', 'search_read',
                            args=[[
                                ('group_id', 'in', group_ids),
                                ('id', 'not in', list(candidate_ids)),
                                ('state', 'not in', ['done', 'cancel']),
                            ]],
                            kwargs={'fields': ['id', 'group_id'], 'limit': 1000},
                        ) or []
                        blocked_groups = {
                            s['group_id'][0]
                            for s in pending_siblings
                            if s.get('group_id')
                        }
                        for p in despachar_candidates:
                            gid = p['group_id'][0] if p.get('group_id') else False
                            if gid and gid not in blocked_groups:
                                despachar.append(p)
                            elif not gid:
                                despachar.append(p)
                    else:
                        despachar = despachar_candidates

            # 3) Mostrador — "En Preparación" = pickings del tipo de
            #    preparación (most_prep_ids) directamente.
            #    "Listo para Entregar" = pickings OUT (most_ids) cuyos
            #    siblings de preparación ya estén todos terminados.

            # 3a) En Preparación: traer pickings directamente del tipo prep
            if most_prep_ids:
                prep_domain = [
                    ('picking_type_id', 'in', most_prep_ids),
                    ('state', 'not in', ['done', 'cancel']),
                ] + filter_domain
                mostrador_preparacion = self._execute_kw(
                    'stock.picking', 'search_read',
                    args=[prep_domain],
                    kwargs={'fields': remote_fields + ['group_id'], 'limit': 500},
                ) or []
                # Aplicar filtro de estados
                if prep_states:
                    mostrador_preparacion = [
                        p for p in mostrador_preparacion
                        if p.get('state') in prep_states
                    ]

            # 3b) Listo para Entregar: traer pickings OUT donde todos los
            #     siblings de preparación estén hechos
            if most_ids:
                mostrador_domain = [
                    ('picking_type_id', 'in', most_ids),
                    ('state', 'not in', ['done', 'cancel']),
                ] + filter_domain
                mostrador_out_all = self._execute_kw(
                    'stock.picking', 'search_read',
                    args=[mostrador_domain],
                    kwargs={'fields': remote_fields + ['group_id'], 'limit': 500},
                ) or []

                if most_prep_ids and mostrador_out_all:
                    group_ids = list({
                        p['group_id'][0]
                        for p in mostrador_out_all
                        if p.get('group_id')
                    })
                    groups_with_pending = set()
                    if group_ids:
                        pending_preps = self._execute_kw(
                            'stock.picking', 'search_read',
                            args=[[
                                ('group_id', 'in', group_ids),
                                ('picking_type_id', 'in', most_prep_ids),
                                ('state', 'not in', ['done', 'cancel']),
                            ]],
                            kwargs={'fields': ['id', 'group_id'], 'limit': 1000},
                        ) or []
                        groups_with_pending = {
                            s['group_id'][0]
                            for s in pending_preps
                            if s.get('group_id')
                        }
                    # Solo los OUT cuyos preps ya terminaron
                    for p in mostrador_out_all:
                        gid = p['group_id'][0] if p.get('group_id') else False
                        if gid and gid in groups_with_pending:
                            pass  # tiene preps pendientes, no va a despachar
                        else:
                            mostrador_despachar.append(p)
                else:
                    # Sin tipo prep definido, todos van a despachar
                    mostrador_despachar = mostrador_out_all

                # Aplicar filtro de estados a despachar
                if desp_states:
                    mostrador_despachar = [
                        p for p in mostrador_despachar
                        if p.get('state') in desp_states
                    ]

            # Resolver sale.order
            all_remote = en_prep + despachar + mostrador_preparacion + mostrador_despachar
            origins = list({p.get('origin') for p in all_remote if p.get('origin')})
            sale_order_map = {}
            if origins:
                try:
                    so_data = self._execute_kw(
                        'sale.order', 'search_read',
                        args=[[('name', 'in', origins)]],
                        kwargs={'fields': ['id', 'name'], 'limit': 500},
                    )
                    for so in (so_data or []):
                        sale_order_map[so['name']] = so['id']
                except Exception:
                    _logger.info("No se pudieron resolver sale.order desde origin")

            # Sub-estados
            all_ids = [p['id'] for p in all_remote]
            state_detail_map = {}
            if all_ids and has_state_detail:
                try:
                    detail_data = self._execute_kw(
                        'stock.picking', 'read',
                        args=[all_ids],
                        kwargs={'fields': ['state_detail_id']},
                    )
                    for d in (detail_data or []):
                        if d.get('state_detail_id'):
                            state_detail_map[d['id']] = d['state_detail_id'][1]
                except Exception:
                    has_state_detail = False
                    _logger.info("Campo state_detail_id no disponible")

            # Líneas de movimiento (stock.move) para Mostrador
            mostrador_move_lines = {}
            mostrador_ids = [p['id'] for p in mostrador_preparacion + mostrador_despachar]
            if mostrador_ids:
                try:
                    move_fields = [
                        'picking_id', 'product_id',
                        'product_uom_qty', 'quantity',
                        'product_uom',
                    ]
                    moves = self._execute_kw(
                        'stock.move', 'search_read',
                        args=[[('picking_id', 'in', mostrador_ids)]],
                        kwargs={'fields': move_fields, 'limit': 5000},
                    ) or []
                    # Fetch product default_code for ZPL
                    _product_ids = list({
                        m['product_id'][0]
                        for m in moves if m.get('product_id')
                    })
                    _product_code_map = {}
                    _product_categ_map = {}
                    if _product_ids:
                        try:
                            _prods = self._execute_kw(
                                'product.product', 'read',
                                args=[_product_ids],
                                kwargs={'fields': ['default_code', 'categ_id']},
                            ) or []
                            _product_code_map = {
                                p['id']: p.get('default_code') or ''
                                for p in _prods
                            }
                            _product_categ_map = {
                                p['id']: p['categ_id'][0] if p.get('categ_id') else 0
                                for p in _prods
                            }
                        except Exception:
                            _logger.info("Could not fetch product default_code/categ_id")
                    for m in moves:
                        pid = m['picking_id'][0] if m.get('picking_id') else False
                        if pid:
                            qty_done = m.get('quantity', m.get('quantity_done', 0))
                            uom_val = m.get('product_uom')
                            if isinstance(uom_val, (list, tuple)):
                                uom_name = uom_val[1] if len(uom_val) > 1 else ''
                            else:
                                uom_name = str(uom_val or '')
                            _prod_id = m['product_id'][0] if m.get('product_id') else 0
                            mostrador_move_lines.setdefault(pid, []).append({
                                'product_name': self._strip_product_ref(
                                    m['product_id'][1] if m.get('product_id') else ''
                                ),
                                'product_qty': m.get('product_uom_qty', 0),
                                'quantity_done': qty_done,
                                'product_uom': uom_name,
                                'default_code': _product_code_map.get(_prod_id, ''),
                                'product_categ_id': _product_categ_map.get(_prod_id, 0),
                            })
                except Exception:
                    _logger.exception("Error al obtener stock.move para Mostrador")

        except Exception:
            _logger.exception("Error al obtener pickings del Odoo remoto")
            raise

        # ---- Log de cambios ----
        Log = self.env['remote.odoo.log'].sudo()
        old_pickings = {
            r['remote_id']: r
            for r in Picking.search_read(
                [('config_id', '=', self.id)],
                ['remote_id', 'name', 'partner_name', 'origin',
                 'state', 'sub_state', 'column_type'],
            )
        }

        new_map = {}
        for col_name, records in [
            ('en_preparacion', en_prep),
            ('despachar', despachar),
            ('mostrador_preparacion', mostrador_preparacion),
            ('mostrador_despachar', mostrador_despachar),
        ]:
            for p in records:
                new_map[p['id']] = {
                    'name': p.get('name', ''),
                    'partner_name': p['partner_id'][1] if p.get('partner_id') else '',
                    'origin': p.get('origin', ''),
                    'state': p.get('state', ''),
                    'sub_state': state_detail_map.get(p['id'], ''),
                    'column_type': col_name,
                }

        col_labels = {
            'en_preparacion': 'En Preparación',
            'despachar': 'Despachar',
            'mostrador_preparacion': 'En Preparación',
            'mostrador_despachar': 'Listo para Entregar',
        }
        state_labels_map = {
            'draft': 'Borrador', 'waiting': 'En espera',
            'confirmed': 'Esperando', 'assigned': 'Disponible',
            'done': 'Hecho', 'cancel': 'Cancelado',
        }
        log_vals = []

        for rid, ndata in new_map.items():
            if rid not in old_pickings:
                log_vals.append({
                    'event_type': 'new',
                    'remote_id': rid,
                    'picking_name': ndata['name'],
                    'partner_name': ndata['partner_name'],
                    'origin': ndata['origin'],
                    'column_type': ndata['column_type'],
                    'new_value': col_labels.get(ndata['column_type'], ndata['column_type']),
                })

        for rid, odata in old_pickings.items():
            if rid not in new_map:
                log_vals.append({
                    'event_type': 'completed',
                    'remote_id': rid,
                    'picking_name': odata.get('name', ''),
                    'partner_name': odata.get('partner_name', ''),
                    'origin': odata.get('origin', ''),
                    'column_type': odata.get('column_type', ''),
                    'old_value': col_labels.get(odata.get('column_type', ''), ''),
                })

        for rid, ndata in new_map.items():
            if rid in old_pickings:
                odata = old_pickings[rid]
                base = {
                    'remote_id': rid,
                    'picking_name': ndata['name'],
                    'partner_name': ndata['partner_name'],
                    'origin': ndata['origin'],
                    'column_type': ndata['column_type'],
                }
                if odata.get('state', '') != ndata['state']:
                    log_vals.append({
                        **base,
                        'event_type': 'state_change',
                        'old_value': state_labels_map.get(odata.get('state', ''), odata.get('state', '')),
                        'new_value': state_labels_map.get(ndata['state'], ndata['state']),
                    })
                old_sub = odata.get('sub_state', '') or ''
                new_sub = ndata['sub_state'] or ''
                if old_sub != new_sub:
                    log_vals.append({
                        **base,
                        'event_type': 'sub_state_change',
                        'old_value': old_sub or '(vacío)',
                        'new_value': new_sub or '(vacío)',
                    })
                if odata.get('column_type', '') != ndata['column_type']:
                    log_vals.append({
                        **base,
                        'event_type': 'column_change',
                        'old_value': col_labels.get(odata.get('column_type', ''), ''),
                        'new_value': col_labels.get(ndata['column_type'], ''),
                    })

        if log_vals:
            Log.create(log_vals)

        # Reemplazar caché
        Picking.search([('config_id', '=', self.id)]).unlink()
        MoveLine.search([('config_id', '=', self.id)]).unlink()

        vals_list = []
        for col_name, records in [
            ('en_preparacion', en_prep),
            ('despachar', despachar),
            ('mostrador_preparacion', mostrador_preparacion),
            ('mostrador_despachar', mostrador_despachar),
        ]:
            for p in records:
                vals_list.append({
                    'config_id': self.id,
                    'remote_id': p['id'],
                    'name': p.get('name', ''),
                    'partner_name': self._clean_partner_name(
                        p['partner_id'][1] if p.get('partner_id') else ''
                    ),
                    'scheduled_date': p.get('scheduled_date') or False,
                    'state': p.get('state', ''),
                    'origin': p.get('origin', ''),
                    'sale_order_remote_id': sale_order_map.get(p.get('origin', ''), 0),
                    'sub_state': state_detail_map.get(p['id'], ''),
                    'picking_type_name': (
                        p['picking_type_id'][1] if p.get('picking_type_id') else ''
                    ),
                    'x_tipo_pedido': p.get('x_Tipo_Pedido') or '',
                    'create_date_remote': p.get('create_date') or False,
                    'column_type': col_name,
                })

        if vals_list:
            Picking.create(vals_list)

        ml_vals = []
        for picking_id, lines in mostrador_move_lines.items():
            for line in lines:
                ml_vals.append({
                    'config_id': self.id,
                    'picking_remote_id': picking_id,
                    'product_name': line.get('product_name') or '',
                    'product_qty': line.get('product_qty') or 0,
                    'quantity_done': line.get('quantity_done') or 0,
                    'product_uom': line.get('product_uom') or '',
                    'default_code': line.get('default_code') or '',
                    'product_categ_id': line.get('product_categ_id') or 0,
                })
        if ml_vals:
            MoveLine.create(ml_vals)

        self.sudo().write({'last_sync': fields.Datetime.now()})
        _logger.info(
            "Sync [%s] OK — Prep: %d | Desp: %d | Most-Prep: %d | Most-Desp: %d",
            self.name, len(en_prep), len(despachar),
            len(mostrador_preparacion), len(mostrador_despachar),
        )

    # -------------------------------------------------------------------------
    # ZPL Label Generation
    # -------------------------------------------------------------------------

    def _get_move_lines_for_zpl(self, remote_id):
        """Return move lines from cache; fetch from remote if missing."""
        self.ensure_one()
        MoveLine = self.env['remote.odoo.move.line'].sudo()

        cached = MoveLine.search([
            ('config_id', '=', self.id),
            ('picking_remote_id', '=', remote_id),
        ])
        if cached:
            return cached

        # Fetch on demand from remote
        move_fields = [
            'picking_id', 'product_id',
            'product_uom_qty', 'quantity',
            'product_uom',
        ]
        moves = self._execute_kw(
            'stock.move', 'search_read',
            args=[[('picking_id', '=', remote_id)]],
            kwargs={'fields': move_fields, 'limit': 500},
        ) or []

        product_ids = list({
            m['product_id'][0] for m in moves if m.get('product_id')
        })
        product_code_map = {}
        product_categ_map = {}
        if product_ids:
            try:
                prods = self._execute_kw(
                    'product.product', 'read',
                    args=[product_ids],
                    kwargs={'fields': ['default_code', 'categ_id']},
                ) or []
                product_code_map = {
                    p['id']: p.get('default_code') or '' for p in prods
                }
                product_categ_map = {
                    p['id']: p['categ_id'][0] if p.get('categ_id') else 0
                    for p in prods
                }
            except Exception:
                _logger.info("Could not fetch product default_code/categ_id on demand")

        vals_list = []
        for m in moves:
            prod_id = m['product_id'][0] if m.get('product_id') else 0
            uom_val = m.get('product_uom')
            if isinstance(uom_val, (list, tuple)):
                uom_name = uom_val[1] if len(uom_val) > 1 else ''
            else:
                uom_name = str(uom_val or '')
            vals_list.append({
                'config_id': self.id,
                'picking_remote_id': remote_id,
                'product_name': self._strip_product_ref(
                    m['product_id'][1] if m.get('product_id') else ''
                ),
                'product_qty': m.get('product_uom_qty', 0),
                'quantity_done': m.get('quantity', m.get('quantity_done', 0)),
                'product_uom': uom_name,
                'default_code': product_code_map.get(prod_id, ''),
                'product_categ_id': product_categ_map.get(prod_id, 0),
            })

        if vals_list:
            return MoveLine.create(vals_list)
        return MoveLine

    def _generate_zpl(self, remote_id):
        """Generate ZPL text based on configured label mode."""
        self.ensure_one()
        Picking = self.env['remote.odoo.picking'].sudo()

        picking = Picking.search([
            ('config_id', '=', self.id),
            ('remote_id', '=', remote_id),
        ], limit=1)
        if not picking:
            return ''

        move_lines = self._get_move_lines_for_zpl(remote_id)

        if self.zpl_label_mode == 'bundle_map':
            return self._generate_zpl_bundle(picking, move_lines)
        elif self.zpl_label_mode == 'simple':
            return self._generate_zpl_simple(picking, move_lines)
        return ''

    def _generate_zpl_simple(self, picking, move_lines):
        """One label per move line filtered by CATEGORY_IDS (telas a cortar)."""
        telas = [
            ml for ml in move_lines
            if ml.product_categ_id in CATEGORY_IDS
        ]
        if not telas:
            return ''

        total_telas = len(telas)
        pedido = picking.origin or picking.name or ''
        cliente = picking.partner_name or ''
        logo_zpl = (self.zpl_logo or '').strip()

        zpl_parts = []
        for idx, ml in enumerate(telas, 1):
            part = (
                "^XA\n"
                "^CI28\n"
                "^PW1500\n"
                "^LL1000\n"
                "\n"
                "^FO70,50\n"
                "^A0R,35,35^FDTelas a cortar: %s/%s^FS\n"
                "\n"
                "^FO150,50\n"
                "^GB4,1100,4^FS\n"
                "\n"
                "^FO300,50\n"
                "^A0R,45,45^FDA cortar: %s mts^FS\n"
                "\n"
                "^FO400,50\n"
                "^A0R,40,40^FD%s^FS\n"
                "\n"
                "^FO500,50\n"
                "^A0R,45,45^FDProducto:^FS\n"
                "\n"
                "^FO600,50\n"
                "^GB4,1100,4^FS\n"
                "\n"
                "^FO620,50\n"
                "^A0R,60,60^FDPedido: %s^FS\n"
                "\n"
                "^FO690,50\n"
                "^A0R,60,60^FD%s^FS\n"
            ) % (
                idx, total_telas,
                int(ml.product_qty) if ml.product_qty == int(ml.product_qty) else ml.product_qty,
                ml.product_name or '',
                pedido, cliente,
            )

            if logo_zpl:
                part += "\n" + logo_zpl + "\n"

            part += "\n^XZ"
            zpl_parts.append(part)

        return "\n".join(zpl_parts)

    def _generate_zpl_bundle(self, picking, move_lines):
        """Labels using BUNDLE_MAP with even distribution."""
        labels = []
        for ml in move_lines:
            ref = ml.default_code or ''
            if ref not in BUNDLE_MAP:
                continue

            qty = ml.product_qty
            upb = BUNDLE_MAP[ref]

            n_bultos = int(qty // upb) + (1 if qty % upb > 0 else 0)
            if n_bultos < 1:
                n_bultos = 1
            base = int(qty // n_bultos)
            extra = int(qty % n_bultos)

            for i in range(n_bultos):
                bqty = base + (1 if i < extra else 0)
                labels.append({
                    'product_name': ml.product_name or '',
                    'qty': bqty,
                    'div_idx': i + 1,
                    'total_div': n_bultos,
                })
        if not labels:
            return ''
        return self._render_zpl_labels(picking, labels)

    def _render_zpl_labels(self, picking, labels):
        """Render ZPL string for a list of label dicts."""
        total_labels = len(labels)
        pedido = picking.origin or picking.name or ''
        cliente = picking.partner_name or ''
        logo_zpl = (self.zpl_logo or '').strip()

        zpl_parts = []
        for idx, lb in enumerate(labels, 1):
            if lb['total_div'] > 1:
                div_texto = 'Div. %s/%s' % (lb['div_idx'], lb['total_div'])
            else:
                div_texto = 'Div. 1/1'

            part = (
                "^XA\n"
                "^CI28\n"
                "^PW1500\n"
                "^LL1000\n"
                "\n"
                "^FO70,50\n"
                "^A0R,35,35^FDEtiqueta: %s/%s^FS\n"
                "\n"
                "^FO150,50\n"
                "^GB4,1100,4^FS\n"
                "\n"
                "^FO300,50\n"
                "^A0R,45,45^FDCantidad: %s u^FS\n"
                "\n"
                "^FO400,50\n"
                "^A0R,40,40^FD%s^FS\n"
                "\n"
                "^FO500,50\n"
                "^A0R,45,45^FD%s^FS\n"
                "\n"
                "^FO600,50\n"
                "^GB4,1100,4^FS\n"
                "\n"
                "^FO620,50\n"
                "^A0R,60,60^FDPedido: %s^FS\n"
                "\n"
                "^FO690,50\n"
                "^A0R,60,60^FD%s^FS\n"
            ) % (
                idx, total_labels, int(lb['qty']),
                lb['product_name'], div_texto, pedido, cliente,
            )

            if logo_zpl:
                part += "\n" + logo_zpl + "\n"

            part += "\n^XZ"
            zpl_parts.append(part)

        return "\n".join(zpl_parts)

    def _send_zpl_to_printer(self, zpl_text):
        """Send ZPL to the configured printer endpoint via HTTP POST."""
        self.ensure_one()
        import urllib.request
        import urllib.parse

        url = (self.zpl_printer_url or '').rstrip('/')
        token = self.zpl_printer_token or ''

        data = urllib.parse.urlencode({
            'token': token,
            'zpl': zpl_text,
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    raise UserError(
                        _('Error al enviar ZPL: HTTP %s') % resp.status
                    )
        except UserError:
            raise
        except Exception as e:
            raise UserError(
                _('Error al enviar ZPL a la impresora: %s') % str(e)
            )

    @api.model
    def print_zpl_label(self, config_id, remote_id):
        """Generate ZPL and send to printer."""
        config = self.sudo().browse(config_id)
        if not config.exists():
            raise UserError(_('Configuración no encontrada.'))
        if config.zpl_label_mode == 'none':
            raise UserError(_('Etiquetas ZPL no configuradas.'))
        if not config.zpl_printer_url or not config.zpl_printer_token:
            raise UserError(_('Configure URL y token de la impresora ZPL.'))

        zpl_text = config._generate_zpl(remote_id)
        if not zpl_text:
            raise UserError(_('No se generó ZPL para este picking.'))

        config._send_zpl_to_printer(zpl_text)
        return True

    @api.model
    def view_zpl_label(self, config_id, remote_id):
        """Generate ZPL and return url to view as text."""
        import base64

        config = self.sudo().browse(config_id)
        if not config.exists():
            raise UserError(_('Configuración no encontrada.'))
        if config.zpl_label_mode == 'none':
            raise UserError(_('Etiquetas ZPL no configuradas.'))

        zpl_text = config._generate_zpl(remote_id)
        if not zpl_text:
            raise UserError(_('No se generó ZPL para este picking.'))

        picking = self.env['remote.odoo.picking'].sudo().search([
            ('config_id', '=', config.id),
            ('remote_id', '=', remote_id),
        ], limit=1)

        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'zpl_%s.txt' % (
                picking.name or 'etiqueta'
            ).replace('/', '_'),
            'type': 'binary',
            'datas': base64.b64encode(zpl_text.encode('utf-8')),
            'mimetype': 'text/plain',
            'public': True,
        })

        return '/web/content/%s?download=false' % attachment.id

    # -------------------------------------------------------------------------
    # Impresión RAW TCP (Ricoh)
    # -------------------------------------------------------------------------

    def _download_picking_pdf(self, remote_id):
        """Descarga el PDF del picking desde el Odoo remoto usando sesión HTTP."""
        import urllib.request
        import http.cookiejar
        import json

        url = self.url.rstrip('/')
        ctx = self._get_ssl_context()

        cookie_jar = http.cookiejar.CookieJar()
        ssl_handler = urllib.request.HTTPSHandler(context=ctx)
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            ssl_handler,
        )

        # Autenticar vía JSON-RPC session
        auth_payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 1,
            'params': {
                'db': self.database,
                'login': self.username,
                'password': self.password,
            },
        }).encode('utf-8')

        auth_req = urllib.request.Request(
            f'{url}/web/session/authenticate',
            data=auth_payload,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with opener.open(auth_req, timeout=30) as resp:
                auth_result = json.loads(resp.read())
        except Exception as e:
            raise UserError(_('No se pudo autenticar para descargar el PDF: %s') % str(e))

        uid = (auth_result.get('result') or {}).get('uid')
        if not uid:
            raise UserError(_('Autenticación HTTP fallida al intentar descargar el PDF.'))

        # Descargar el PDF
        pdf_url = f'{url}/report/pdf/stock.report_picking/{remote_id}'
        pdf_req = urllib.request.Request(pdf_url)
        try:
            with opener.open(pdf_req, timeout=60) as resp:
                pdf_data = resp.read()
        except Exception as e:
            raise UserError(_('No se pudo descargar el PDF del picking: %s') % str(e))

        if not pdf_data:
            raise UserError(_('El PDF descargado está vacío.'))
        return pdf_data

    @staticmethod
    def _send_raw_tcp(data, host, port, timeout=10.0):
        """Envía bytes crudos a una impresora por socket TCP RAW."""
        import socket
        with socket.create_connection((host, int(port)), timeout=float(timeout)) as sock:
            sock.sendall(data)
            try:
                sock.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            try:
                sock.recv(1024)
            except Exception:
                pass

    @api.model
    def print_picking_ricoh(self, config_id, remote_id):
        """Descarga el PDF del picking y lo envía a la impresora Ricoh por TCP RAW."""
        config = self.sudo().browse(config_id)
        if not config.exists():
            raise UserError(_('Configuración no encontrada.'))
        if not config.enable_ricoh_print:
            raise UserError(_('La impresión por red no está habilitada en esta configuración.'))
        if not config.ricoh_host or not config.ricoh_port:
            raise UserError(_('Configure el host y el puerto de la impresora Ricoh.'))

        pdf_data = config._download_picking_pdf(remote_id)
        try:
            config._send_raw_tcp(
                pdf_data,
                config.ricoh_host,
                config.ricoh_port,
                timeout=config.ricoh_timeout or 10.0,
            )
        except Exception as e:
            raise UserError(_('Error al enviar el PDF a la impresora: %s') % str(e))
        return True

    # -------------------------------------------------------------------------
    # API para el dashboard JS
    # -------------------------------------------------------------------------

    @api.model
    def get_dashboard_data(self, config_id=False):
        config = self.sudo().browse(config_id) if config_id else self.sudo().search([], limit=1)
        if not config.exists():
            return {'configured': False}

        Picking = self.env['remote.odoo.picking'].sudo()
        MoveLine = self.env['remote.odoo.move.line'].sudo()

        all_pickings = Picking.search_read(
            [('config_id', '=', config.id)],
            ['remote_id', 'name', 'partner_name', 'scheduled_date',
             'state', 'state_label', 'origin', 'sale_order_remote_id',
             'column_type', 'picking_type_name', 'sub_state',
             'x_tipo_pedido', 'create_date_remote'],
            order='scheduled_date asc, name asc',
        )

        all_move_lines = MoveLine.search_read(
            [('config_id', '=', config.id)],
            ['picking_remote_id', 'product_name', 'product_qty',
             'quantity_done', 'product_uom'],
            order='product_name asc',
        )
        move_lines_map = {}
        for ml in all_move_lines:
            ml_data = {
                'product_name': ml.get('product_name') or '',
                'product_qty': ml.get('product_qty') or 0,
                'quantity_done': ml.get('quantity_done') or 0,
                'product_uom': ml.get('product_uom') or '',
            }
            move_lines_map.setdefault(ml['picking_remote_id'], []).append(ml_data)

        # Compute waiting minutes
        now = fields.Datetime.now()
        for p in all_pickings:
            p['partner_name'] = self._clean_partner_name(p.get('partner_name') or '')
            cdate = p.get('create_date_remote')
            if cdate:
                if isinstance(cdate, str):
                    from datetime import datetime
                    try:
                        cdate = datetime.strptime(cdate, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        cdate = None
                if cdate:
                    delta = now - cdate
                    p['waiting_minutes'] = int(delta.total_seconds() / 60)
                else:
                    p['waiting_minutes'] = 0
            else:
                p['waiting_minutes'] = 0

        visible_columns = []
        column_labels = {
            'en_preparacion': 'En Preparación',
            'despachar': 'Despachar',
            'mostrador_preparacion': 'En Preparación',
            'mostrador_despachar': 'Listo para Entregar',
        }
        if config.show_en_preparacion:
            visible_columns.append('en_preparacion')
        if config.show_despachar:
            visible_columns.append('despachar')
        if config.show_mostrador_preparacion:
            visible_columns.append('mostrador_preparacion')
        if config.show_mostrador_despachar:
            visible_columns.append('mostrador_despachar')

        buckets = {vc: [] for vc in visible_columns}
        for p in all_pickings:
            col = p.get('column_type')
            if col in buckets:
                if col in ('mostrador_preparacion', 'mostrador_despachar'):
                    p['move_lines'] = move_lines_map.get(p['remote_id'], [])
                buckets[col].append(p)

        columns = {}
        for col_key, items in buckets.items():
            columns[col_key] = {'items': items, 'label': column_labels.get(col_key, col_key)}

        return {
            'configured': True,
            'config_id': config.id,
            'dashboard_name': config.name,
            'remote_url': (config.url or '').rstrip('/'),
            'last_sync': (
                fields.Datetime.to_string(config.last_sync) if config.last_sync else False
            ),
            'visible_columns': visible_columns,
            'columns': columns,
            'zpl_label_mode': config.zpl_label_mode or 'none',
            'has_zpl_printer': bool(config.zpl_printer_url and config.zpl_printer_token),
            'has_ricoh_printer': bool(
                config.enable_ricoh_print and config.ricoh_host and config.ricoh_port
            ),
        }

    @api.model
    def get_dashboard_kpis(self, config_id=False):
        Log = self.env['remote.odoo.log'].sudo()
        today_start = fields.Datetime.to_string(
            fields.Datetime.now().replace(hour=0, minute=0, second=0)
        )
        return {
            'completed_today': Log.search_count([
                ('event_type', '=', 'completed'),
                ('timestamp', '>=', today_start),
            ]),
            'new_today': Log.search_count([
                ('event_type', '=', 'new'),
                ('timestamp', '>=', today_start),
            ]),
            'state_changes_today': Log.search_count([
                ('event_type', 'in', ['state_change', 'sub_state_change']),
                ('timestamp', '>=', today_start),
            ]),
        }

    @api.model
    def action_sync_pickings(self, config_id=False):
        if config_id:
            config = self.sudo().browse(config_id)
        else:
            config = self.sudo().search([], limit=1)
        if not config.exists():
            raise UserError(_('Debe configurar la conexión primero.'))
        config.sync_pickings()
        return True

    @api.model
    def cron_sync_all(self):
        for config in self.sudo().search([]):
            try:
                config.sync_pickings()
            except Exception:
                _logger.exception("Error syncing dashboard '%s'", config.name)

    @api.model
    def validate_remote_picking(self, config_id, remote_id):
        config = self.sudo().browse(config_id)
        if not config.exists():
            raise UserError(_('Configuración no encontrada.'))
        try:
            config._execute_kw(
                'stock.picking', 'button_validate',
                args=[[remote_id]],
            )
        except Exception as e:
            _logger.exception("Error al validar picking remoto %s", remote_id)
            raise UserError(_('Error al validar el picking: %s') % str(e))
        config.sync_pickings()
        return True

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def write(self, vals):
        credential_fields = {'url', 'database', 'username', 'password'}
        if credential_fields & set(vals.keys()):
            vals['remote_uid'] = False
        return super().write(vals)
