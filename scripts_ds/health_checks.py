import subprocess
import socket
import salt.utils
import logging
import os
import re
import json

__author__ = "Dzmitry Stremkouski"
__copyright__ = "Copyright 2019, Mirantis Inc."
__license__ = "Apache 2.0"

logger = logging.getLogger(__name__)
stream = logging.StreamHandler()
logger.addHandler(stream)


def _failed_minions(out, agent, failed_minions):

    ''' Verify failed minions '''

    if len(failed_minions) > 0:
        logger.error("%s check FAILED" % agent)
        logger.error("Some minions returned non-zero exit code or empty data")
        logger.error("Failed minions:" + str(failed_minions))
        for minion in failed_minions:
            logger.error(minion)
            logger.debug(str(out[minion]['ret']))
        __context__['retcode'] = 2
        return False

    return True


def _minions_output(out, agent, ignore_dead, ignore_empty=False):

    ''' Verify minions output and exit code '''

    if not out:
        logger.error("%s check FAILED" % agent)
        logger.error("No response from master cmd")
        __context__['retcode'] = 2
        return False

    if not ignore_dead:
        jid = out.itervalues().next()['jid']
        job_stats = __salt__['saltutil.runner']( 'jobs.print_job', arg=[jid] ) or None
        if not job_stats:
            logger.error("%s check FAILED" % agent)
            logger.error("No response from master runner")
            __context__['retcode'] = 2
            return False

        job_result = job_stats[jid]['Result']
        job_minions = job_stats[jid]['Minions']
        if len(job_minions) != len(job_result):
            logger.error("%s check FAILED" % agent)
            logger.error("Some minions are offline")
            logger.error(list(set(job_minions) - set(job_result.keys())))
            __context__['retcode'] = 2
            return False

    failed_minions = []
    for minion in out:
        if 'retcode' in out[minion]:
            if out[minion]['retcode'] == 0:
                if not ignore_empty:
                    if isinstance(out[minion]['ret'], bool):
                        if minion not in failed_minions:
                            failed_minions.append(minion)
                    elif len(out[minion]['ret']) == 0:
                        if minion not in failed_minions:
                            failed_minions.append(minion)
            else:
                if minion not in failed_minions:
                    failed_minions.append(minion)
        else:
            if minion not in failed_minions:
                failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    return True


def minions_check(wait_timeout=1, gather_job_wait_timeout=1, target='*', target_type='glob', ignore_dead=False):

    ''' Verify minions are online '''

    agent = "Minions"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='test.ping',
                                    timeout=wait_timeout,
                                    gather_job_timeout=gather_job_wait_timeout
                                  ) or None

    return _minions_output(out, agent, ignore_dead, ignore_empty=True)


def time_diff_check(time_diff=1, target='*', target_type='glob', ignore_dead=False, **kwargs):

    ''' Verify time diff on servers '''

    agent = "Time diff"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='status.time',
                                    arg=['%s'],
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    minions_times = {}
    env_times = []
    verified_minions = []

    for minion in out:
        verified_minions.append(minion)
        if out[minion]['retcode'] == 0:
            minion_time = int(out[minion]['ret'])
            if str(minion_time) not in minions_times:
                minions_times[str(minion_time)] = []
            minions_times[str(minion_time)].append(minion)
            env_times.append(minion_time)

    env_times.sort()
    diff = env_times[-1] - env_times[0]

    if diff > time_diff:
        __context__['retcode'] = 2
        if kwargs.get("debug", False):
            return False, minions_times
        else:
            return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def contrail_check(target='I@contrail:control or I@contrail:collector or I@opencontrail:compute or I@opencontrail:client', target_type='compound', ignore_dead=False, **kwargs):

    ''' Verify contrail status returns nothing critical '''

    agent = "Contrail status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='cmd.run',
                                    arg=['contrail-status'],
                                    timeout=5
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    pattern = '^(==|$|\S+\s+(active|backup|inactive\s\(disabled\son\sboot\)))'
    prog = re.compile(pattern)

    validated = []
    for minion in out:
        for line in out[minion]['ret'].split('\n'):
            if not prog.match(line) and minion not in failed_minions:
                failed_minions.append(minion)
        validated.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(validated)
    return True


def galera_check(cluster_size=3, target='I@galera:master or I@galera:slave', target_type='compound', ignore_dead=False, **kwargs):

    ''' Verify galera cluster size and state '''

    agent = "Galera status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='mysql.status',
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []

    validated = []
    for minion in out:
        if int(out[minion]['ret']['wsrep_cluster_size']) != int(cluster_size) and minion not in failed_minions:
            failed_minions.append(minion)
        if out[minion]['ret']['wsrep_evs_state'] != 'OPERATIONAL' and minion not in failed_minions:
            failed_minions.append(minion)
        validated.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(validated)
        logger.info("Cluster size: " + str(out[validated[0]]['ret']['wsrep_cluster_size']))
        logger.info("Cluster state: " + str(out[validated[0]]['ret']['wsrep_evs_state']))
    return True


def _quote_str(s, l=False, r=False):

    ''' Quting rabbitmq erl objects for json import '''

    if len(s) > 0:
        if l:
            s = s.lstrip()
        if r:
            s = s.rstrip()
        if (s[0] == "'") and (s[-1] != "'") and r and not l:
            s += "'"
        if (s[0] == '"') and (s[-1] != '"') and r and not l:
            s += '"'
        if (s[-1] == "'") and (s[0] != "'") and l and not r:
            s = "'" + s
        if (s[-1] == '"') and (s[0] != '"') and l and not r:
            s = '"' + s
        if (s[-1] != "'") and (s[-1] != '"') and (s[0] != "'") and (s[0] != '"'):
            s = '"' + s.replace('"', '\\\"') + '"'
        else:
            if (not l) and (not r) and s[0] != '"' and not s[-1] != '"':
                s= s.replace('"', '\\\"')
        return s.replace("'", '"')
    else:
        return s


def _sanitize_rmqctl_output(string):

    ''' Sanitizing rabbitmq erl objects for json import '''

    rabbitctl_json = ""
    for line in string.split(','):
        copy = line
        left = ""
        right = ""
        mid = copy
        lpar = False
        rpar = False
        if re.search('([\[\{\s]+)(.*)', copy):
            mid = re.sub('^([\[\{\s]+)','', copy)
            left = copy[:-len(mid)]
            copy = mid
            lpar = True
        if re.search('(.*)([\]\}\s]+)$', copy):
            mid = re.sub('([\]\}\s]+)$','', copy)
            right = copy[len(mid):]
            copy = mid
            rpar = True
        result = left + _quote_str(mid, l=lpar, r=rpar) + right
        if (not rpar) and lpar and (len(left.strip()) > 0) and (left.strip()[-1] == '{'):
            result += ":"
        else:
            result += ","
        rabbitctl_json += result

    rabbitctl_json = rabbitctl_json[:-1]
    new_rabbitctl_json = rabbitctl_json
    for s in re.findall('"[^:\[{\]}]+"\s*:\s*("[^\[{\]}]+")', rabbitctl_json):
        if '"' in s[1:][:-1]:
            orig = s
            changed = '"' + s.replace('\\', '\\\\').replace('"', '\\\"') + '"'
            new_rabbitctl_json = new_rabbitctl_json.replace(orig, changed)
    return new_rabbitctl_json


def rabbitmq_cmd(cmd):

    ''' JSON formatted RabbitMQ command output '''

    supported_commands = ['status', 'cluster_status', 'list_hashes', 'list_ciphers']
    if cmd not in supported_commands:
        logger.error("Command is not supported yet, sorry")
        logger.error("Supported commands are: " + str(supported_commands))
        __context__['retcode'] = 2
        return False

    proc = subprocess.Popen(['rabbitmqctl', cmd], stdout=subprocess.PIPE)
    stdout, stderr =  proc.communicate()

    rabbitmqctl_cutoff = stdout[int(stdout.find('[')):int(stdout.rfind(']'))+1].replace('\n','')
    return json.loads(_sanitize_rmqctl_output(rabbitmqctl_cutoff))


def rabbitmq_check(target='I@rabbitmq:server', target_type='compound', ignore_dead=False, **kwargs):

    ''' Verify rabbit cluster and it's alarms '''

    agent = "RabbitMQ status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='health_checks.rabbitmq_cmd',
                                    arg=['cluster_status'],
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []

    for minion in out:
        rabbitmqctl_json = out[minion]['ret']
        running_nodes = []
        available_nodes = []
        alarms = []
        for el in rabbitmqctl_json:
            if 'alarms' in el:
                alarms = el['alarms']
            if 'nodes' in el:
                available_nodes = el['nodes'][0]['disc']
            if 'running_nodes' in el:
                running_nodes = el['running_nodes']

        if running_nodes.sort() == available_nodes.sort():
            nodes_alarms = []
            for node in running_nodes:
                for el in alarms:
                    if node in el:
                        if len(el[node]) > 0:
                            nodes_alarms.append(el[node])
            if len(nodes_alarms) > 0:
                failed_minions.append(minion)
        else:
            failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(running_nodes)
    return True


def haproxy_status(socket_path='/run/haproxy/admin.sock', buff_size = 8192, encoding = 'UTF-8', stats_filter=[]):

    ''' JSON formatted haproxy status '''

    stat_cmd = 'show stat\n'

    if not os.path.exists(socket_path):
        logger.error('Socket %s does not exist or haproxy not running' % socket_path)
        __context__['retcode'] = 2
        return False

    client = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(socket_path)
    stat_cmd = 'show stat\n'

    client.send(bytearray(stat_cmd, encoding))
    output = client.recv(buff_size)

    res = ""
    while output:
        res += output.decode(encoding)
        output = client.recv(buff_size)
    client.close()

    haproxy_stats = {}
    res_list = res.split('\n')
    fields = res_list[0][2:].split(',')
    stats_list = []
    for line in res_list[1:]:
        if len(line.strip()) > 0:
            stats_list.append(line)

    for i in range(len(stats_list)):
        element = {}
        for n in fields:
            element[n] = stats_list[i].split(',')[fields.index(n)]
        server_name = element.pop('pxname')
        server_type = element.pop('svname')
        if stats_filter:
            filtered_element = element.copy()
            for el in element:
                if el not in stats_filter:
                    filtered_element.pop(el)
            element = filtered_element
        if server_name not in haproxy_stats:
            haproxy_stats[server_name] = {}
        if server_type == "FRONTEND" or server_type == "BACKEND":
            haproxy_stats[server_name][server_type] = element
        else:
            if 'UPSTREAM' not in haproxy_stats[server_name]:
                haproxy_stats[server_name]['UPSTREAM'] = {}
            haproxy_stats[server_name]['UPSTREAM'][server_type] = element

    return haproxy_stats


def haproxy_check(target='I@haproxy:proxy', target_type='compound', ignore_dead=False, ignore_services=[], ignore_upstreams=[], ignore_no_upstream=False, **kwargs):

    ''' Verify haproxy backends status '''

    agent = "haproxy status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='health_checks.haproxy_status',
                                    arg=["stats_filter=['status']"],
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        verified_minions.append(minion)
        haproxy_json = out[minion]['ret']
        for service in haproxy_json:
            if service not in ignore_services:
                if haproxy_json[service]['FRONTEND']['status'] != 'OPEN':
                    if minion not in failed_minions:
                        failed_minions.append(minion)
                if haproxy_json[service]['BACKEND']['status'] != 'UP':
                    if minion not in failed_minions:
                        failed_minions.append(minion)
                if 'UPSTREAM' in haproxy_json[service]:
                    for upstream in haproxy_json[service]['UPSTREAM']:
                        if upstream not in ignore_upstreams:
                            if haproxy_json[service]['UPSTREAM'][upstream]['status'] != 'UP':
                                if minion not in failed_minions:
                                    failed_minions.append(minion)
                else:
                    if not ignore_no_upstream:
                        if minion not in failed_minions:
                            failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def df_check(target='*', target_type='glob', verify='space', space_limit=80, inode_limit=80, ignore_dead=False, ignore_partitions=[], **kwargs):

    ''' Verify storage space/inodes status '''

    supported_options = ['space', 'inodes']
    if verify not in supported_options:
        logger.error('Unsupported "verify" option.')
        logger.error('Supported options are: %s' % str(supported_options))
        __context__['retcode'] = 2
        return False

    if verify == 'space':
        fun_cmd = 'disk.usage'
        json_arg = 'capacity'
        limit = space_limit
    elif verify == 'inodes':
        fun_cmd = 'disk.inodeusage'
        json_arg = 'use'
        limit = inode_limit

    agent = "df status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun=fun_cmd,
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        verified_minions.append(minion)
        df_json = out[minion]['ret']
        for disk in df_json:
            if disk not in ignore_partitions:
                if int(df_json[disk][json_arg][:-1]) > int(limit):
                    if minion not in failed_minions:
                        failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def load_check(target='*', target_type='glob', la1=3, la5=3, la15=3, ignore_dead=False, **kwargs):

    ''' Verify load average status '''

    agent = "load average status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='status.loadavg',
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        verified_minions.append(minion)
        la_json = out[minion]['ret']
        if float(la_json['1-min']) > float(la1):
            if minion not in failed_minions:
                failed_minions.append(minion)
        if float(la_json['5-min']) > float(la5):
            if minion not in failed_minions:
                failed_minions.append(minion)
        if float(la_json['15-min']) > float(la15):
            if minion not in failed_minions:
                failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def netdev_check(target='*', target_type='glob', rx_drop_limit=0, tx_drop_limit=0, ignore_devices=[], ignore_dead=False, **kwargs):

    ''' Verify netdev rx/tx drop status '''

    agent = "netdev rx/tx status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='status.netdev',
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        verified_minions.append(minion)
        dev_json = out[minion]['ret']
        for netdev in dev_json:
            if netdev not in ignore_devices:
                if int(dev_json[netdev]['rx_drop']) > int(rx_drop_limit):
                    if minion not in failed_minions:
                        failed_minions.append(minion)
                if int(dev_json[netdev]['tx_drop']) > int(tx_drop_limit):
                    if minion not in failed_minions:
                        failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def mem_check(target='*', target_type='glob', used_limit=80, ignore_dead=False, **kwargs):

    ''' Verify available memory status '''

    agent = "available memory status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='status.meminfo',
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        mem_avail = int(out[minion]['ret']['MemAvailable']['value'])
        mem_total = int(out[minion]['ret']['MemTotal']['value'])
        used_pct = float((mem_total - mem_avail) * 100 / mem_total)
        if used_pct > float(used_limit):
            if minion not in failed_minions:
                        failed_minions.append(minion)
        else:
            verified_minions.append( { minion : str(used_pct) + '%' } )

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True


def ntp_status(params = ['-4', '-p', '-n']):

    ''' JSON formatted ntpq command output '''

    ntp_states = [
      { 'indicator': '#', 'comment': 'source selected, distance exceeds maximum value' },
      { 'indicator': 'o', 'comment': 'source selected, Pulse Per Second (PPS) used' },
      { 'indicator': '+', 'comment': 'source selected, included in final set' },
      { 'indicator': 'x', 'comment': 'source false ticker' },
      { 'indicator': '.', 'comment': 'source selected from end of candidate list' },
      { 'indicator': '-', 'comment': 'source discarded by cluster algorithm' },
      { 'indicator': '*', 'comment': 'current time source' },
      { 'indicator': ' ', 'comment': 'source discarded high stratum, failed sanity' }
    ]
    ntp_state_indicators = []
    for state in ntp_states:
        ntp_state_indicators.append(state['indicator'])
    source_types = {}
    source_types['l'] = "local (such as a GPS, WWVB)"
    source_types['u'] = "unicast (most common)"
    source_types['m'] = "multicast"
    source_types['b'] = "broadcast"
    source_types['-'] = "netaddr"

    proc = subprocess.Popen(['ntpq'] + params, stdout=subprocess.PIPE)
    stdout, stderr =  proc.communicate()

    ntp_lines = stdout.split('\n')
    fields = re.sub("\s+", " ", ntp_lines[0]).split()
    fields[fields.index('st')] = 'stratum'
    fields[fields.index('t')] = 'source_type'

    ntp_peers = {}
    for line in ntp_lines[2:]:
        if len(line.strip()) > 0:
            element = {}
            values = re.sub("\s+", " ", line).split()
            for i in range(len(values)):
                if fields[i] == 'source_type':
                    element[fields[i]] = { 'indicator': values[i], 'comment': source_types[values[i]] }
                elif fields[i] in ['stratum', 'when', 'poll', 'reach']:
                    if values[i] == '-':
                        element[fields[i]] = int(-1)
                    else:
                        element[fields[i]] = int(values[i])
                elif fields[i] in ['delay', 'offset', 'jitter']:
                    element[fields[i]] = float(values[i])
                else:
                    element[fields[i]] = values[i]
            peer = element.pop('remote')
            peer_state = peer[0]
            if peer_state in ntp_state_indicators:
                peer = peer[1:]
            else:
                peer_state = 'f'
            element['current'] = False
            if peer_state == '*':
                element['current'] = True
            for state in ntp_states:
                if state['indicator'] == peer_state:
                    element['state'] = state.copy()
                if peer_state == 'f' and state['indicator'] == ' ':
                    fail_state = state.copy()
                    fail_state.pop('indicator')
                    fail_state['indicator'] = 'f'
                    element['state'] = fail_state
            ntp_peers[peer] = element

    return ntp_peers


def ntp_check(min_peers=1, max_stratum=3, target='*', target_type='glob', ignore_dead=False, **kwargs):

    ''' Verify NTP peers status '''

    agent = "ntpd peers status"
    out = __salt__['saltutil.cmd']( tgt=target,
                                    tgt_type=target_type,
                                    fun='health_checks.ntp_status',
                                    timeout=3
                                  ) or None

    if not _minions_output(out, agent, ignore_dead):
        __context__['retcode'] = 2
        return False

    failed_minions = []
    verified_minions = []
    for minion in out:
        ntp_json = out[minion]['ret']
        good_peers = []
        for peer in ntp_json:
            if ntp_json[peer]['stratum'] < int(max_stratum) + 1:
                good_peers.append(peer)
        if len(good_peers) > int(min_peers) - 1:
            if minion not in verified_minions:
                verified_minions.append(minion)
        else:
            if minion not in failed_minions:
                failed_minions.append(minion)

    if not _failed_minions(out, agent, failed_minions):
        __context__['retcode'] = 2
        return False

    if kwargs.get("debug", False):
        logger.info(verified_minions)
    return True
