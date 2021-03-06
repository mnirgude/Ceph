# -*- coding: utf-8 -*-
from __future__ import absolute_import

from . import ApiController, AuthRequired, RESTController
from .. import mgr, logger
from ..services.ceph_service import CephService
from ..services.exception import handle_send_command_error
from ..tools import str_to_bool


@ApiController('/osd')
@AuthRequired()
class Osd(RESTController):
    def list(self):
        osds = self.get_osd_map()
        # Extending by osd stats information
        for s in mgr.get('osd_stats')['osd_stats']:
            osds[str(s['osd'])].update({'osd_stats': s})
        # Extending by osd node information
        nodes = mgr.get('osd_map_tree')['nodes']
        osd_tree = [(str(o['id']), o) for o in nodes if o['id'] >= 0]
        for o in osd_tree:
            osds[o[0]].update({'tree': o[1]})
        # Extending by osd parent node information
        hosts = [(h['name'], h) for h in nodes if h['id'] < 0]
        for h in hosts:
            for o_id in h[1]['children']:
                if o_id >= 0:
                    osds[str(o_id)]['host'] = h[1]
        # Extending by osd histogram data
        for o_id in osds:
            o = osds[o_id]
            o['stats'] = {}
            o['stats_history'] = {}
            osd_spec = str(o['osd'])
            for s in ['osd.op_w', 'osd.op_in_bytes', 'osd.op_r', 'osd.op_out_bytes']:
                prop = s.split('.')[1]
                o['stats'][prop] = CephService.get_rate('osd', osd_spec, s)
                o['stats_history'][prop] = CephService.get_rates('osd', osd_spec, s)
            # Gauge stats
            for s in ['osd.numpg', 'osd.stat_bytes', 'osd.stat_bytes_used']:
                o['stats'][s.split('.')[1]] = mgr.get_latest('osd', osd_spec, s)
        return list(osds.values())

    def get_osd_map(self):
        osds = {}
        for osd in mgr.get('osd_map')['osds']:
            osd['id'] = osd['osd']
            osds[str(osd['id'])] = osd
        return osds

    @handle_send_command_error('osd')
    def get(self, svc_id):
        histogram = CephService.send_command('osd', srv_spec=svc_id, prefix='perf histogram dump')
        return {
            'osd_map': self.get_osd_map()[svc_id],
            'osd_metadata': mgr.get_metadata('osd', svc_id),
            'histogram': histogram,
        }

    @RESTController.Resource('POST', query_params=['deep'])
    def scrub(self, svc_id, deep=False):
        api_scrub = "osd deep-scrub" if str_to_bool(deep) else "osd scrub"
        CephService.send_command("mon", api_scrub, who=svc_id)


@ApiController('/osd/flags')
class OsdFlagsController(RESTController):
    @staticmethod
    def _osd_flags():
        enabled_flags = mgr.get('osd_map')['flags_set']
        if 'pauserd' in enabled_flags and 'pausewr' in enabled_flags:
            # 'pause' is set by calling `ceph osd set pause` and unset by
            # calling `set osd unset pause`, but `ceph osd dump | jq '.flags'`
            # will contain 'pauserd,pausewr' if pause is set.
            # Let's pretend to the API that 'pause' is in fact a proper flag.
            enabled_flags = list(
                set(enabled_flags) - {'pauserd', 'pausewr'} | {'pause'})
        return sorted(enabled_flags)

    def list(self):
        return self._osd_flags()

    def bulk_set(self, flags):
        """
        The `recovery_deletes` and `sortbitwise` flags cannot be unset.
        `purged_snapshots` cannot even be set. It is therefore required to at
        least include those three flags for a successful operation.
        """
        assert isinstance(flags, list)

        enabled_flags = set(self._osd_flags())
        data = set(flags)
        added = data - enabled_flags
        removed = enabled_flags - data
        for flag in added:
            CephService.send_command('mon', 'osd set', '', key=flag)
        for flag in removed:
            CephService.send_command('mon', 'osd unset', '', key=flag)
        logger.info('Changed OSD flags: added=%s removed=%s', added, removed)

        return sorted(enabled_flags - removed | added)
