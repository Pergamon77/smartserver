import threading
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from datetime import datetime, timedelta
import traceback

from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.core.exceptions import FritzLookUpError
from fritzconnection.core.exceptions import FritzConnectionException
from fritzconnection.core.exceptions import FritzServiceError

from lib.handler import _handler
from lib.dto.device import Connection
from lib.dto.group import Group
from lib.dto.event import Event


class Fritzbox(_handler.Handler): 
    def __init__(self, config, cache ):
        super().__init__()
      
        self.config = config
        self.cache = cache
        
        self.is_running = True
        
        self.sessions = {}
        
        self.next_run = {}
        
        self.has_wifi_networks = False
        self.wifi_networks = {}

        self.wifi_associations = {}
        self.wifi_clients = {}
        
        self.dhcp_clients = {}
        
        self.known_clients = {}
        self.fritzbox_macs = {}
        
        #self.uid_macs_map = {}
        #self.uid_child_mac_map = {}
        #self.child_mac_parent_mac_map = {}
        
        self.devices = {}

        self.fc = {}
        self.fh = {}
        for fritzbox_ip in self.config.fritzbox_devices:
            self.fc[fritzbox_ip] = FritzConnection(address=fritzbox_ip, user=self.config.fritzbox_username, password=self.config.fritzbox_password)
            self.fh[fritzbox_ip] = FritzHosts(address=fritzbox_ip, user=self.config.fritzbox_username, password=self.config.fritzbox_password)
        
        self.condition = threading.Condition()
        self.thread = threading.Thread(target=self._checkFritzbox, args=())
        
        self.delayed_lock = threading.Lock()
        self.delayed_devices = {}
        self.delayed_wakeup_timer = None
        
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    def start(self):
        self.thread.start()
        
    def terminate(self):
        with self.condition:
            self.is_running = False
            self.condition.notifyAll()
            
    def _checkFritzbox(self):
        was_suspended = {}
        
        now = datetime.now()
        for fritzbox_ip in self.config.fritzbox_devices:
            self.next_run[fritzbox_ip] = {"device": now, "dhcp_clients": now, "mesh_clients": now}

            self.wifi_networks[fritzbox_ip] = {}
            
            self.wifi_associations[fritzbox_ip] = {}
            self.wifi_clients[fritzbox_ip] = {}
            
            self.known_clients[fritzbox_ip] = {}
            self.dhcp_clients[fritzbox_ip] = {}
            
            self.fritzbox_macs[fritzbox_ip] = None
            
            was_suspended[fritzbox_ip] = False
        
        while self.is_running:
            events = []

            timeout = 9999999999
            
            for fritzbox_ip in self.config.fritzbox_devices:
                try:
                    if was_suspended[fritzbox_ip]:
                        logging.warning("Resume Fritzbox '{}'.".format(fritzbox_ip))
                        was_suspended[fritzbox_ip] = False
                        
                    self._processDevice(fritzbox_ip, events)
                except FritzConnectionException as e:
                    logging.error("Fritzbox '{}' not accessible. Will suspend for 1 minutes.".format(fritzbox_ip))
                    logging.error(traceback.format_exc())
                    if timeout > 60:
                        timeout = 60
                    was_suspended[fritzbox_ip] = True
                except Exception as e:
                    self.cache.cleanLocks(self, events)

                    logging.error("Fritzbox '{}' got unexpected exception. Will suspend for 15 minutes.".format(fritzbox_ip))
                    logging.error(traceback.format_exc())
                    if timeout > self.config.remote_error_timeout:
                        timeout = self.config.remote_error_timeout
                    was_suspended[fritzbox_ip] = True
                    
            if len(events) > 0:
                self._getDispatcher().dispatch(self,events)

            now = datetime.now()
            for fritzbox_ip in self.config.fritzbox_devices:
                for next_run in self.next_run[fritzbox_ip].values():
                    diff = (next_run - now).total_seconds()
                    if diff < timeout:
                        timeout = diff

            if timeout > 0:
                with self.condition:
                    self.condition.wait(timeout)
                    
    def _processDevice(self, fritzbox_ip, events):
        #https://fritzconnection.readthedocs.io/en/1.9.1/sources/library.html#fritzhosts

        # needs to run first to find fritzbox mac on startup
        if self.next_run[fritzbox_ip]["dhcp_clients"] <= datetime.now():
            self._fetchDHCPClients(fritzbox_ip, events)

        if self.next_run[fritzbox_ip]["mesh_clients"] <= datetime.now():
            self._fetchMeshClients(fritzbox_ip, events)
                
        if self.next_run[fritzbox_ip]["device"] <= datetime.now():
            self._fetchDeviceInfo(fritzbox_ip, events)
    
    def _fetchMeshClients(self, fritzbox_ip, events):
        self.next_run[fritzbox_ip]["mesh_clients"] = datetime.now() + timedelta(seconds=self.config.fritzbox_client_interval)

        mesh_hops = {}
        #mesh_nodes = {}
        
        start = datetime.now().timestamp()
        topologie = self.fh[fritzbox_ip].get_mesh_topology()
        logging.info("Mesh data of '{}' fetched in {} seconds".format(fritzbox_ip, datetime.now().timestamp() - start))
        
        self.cache.lock(self)
        
        # ************ Prepare wifi networks ****************
        node_link_wifi_map = {}
        _active_networks = {}
        for node in topologie["nodes"]:
            for node_interface in node["node_interfaces"]:
                if node_interface["type"] != "WLAN":
                    continue
                
                if node_interface["ssid"]:
                    ssid = node_interface["ssid"]
                    channel = node_interface["current_channel"]
                    band = "5g" if channel > 13 else "2g"
                    priority = 1 if channel > 13 else 0
                    
                    gid = "{}-{}-{}".format(fritzbox_ip,band,ssid)
                    network = {
                        "gid": gid,
                        "ssid": ssid,
                        "band": band,
                        "priority": priority,
                        "vlan": self.config.default_vlan,
                        "channel": channel
                    }
                    self.wifi_networks[fritzbox_ip][gid] = network
                    _active_networks[gid] = network
                    
                    for node_link in node_interface["node_links"]:
                        node_link_wifi_map[node_link["uid"]] = network
                    
        if _active_networks or self.wifi_networks[fritzbox_ip]:
            for gid in _active_networks:
                network = _active_networks[gid]

                group = self.cache.getGroup(gid, Group.WIFI)
                group.setDetail("ssid", network["ssid"], "string")
                group.setDetail("band", network["band"], "string")
                group.setDetail("channel", network["channel"], "string")
                group.setDetail("priority", network["priority"], "hidden")
                self.cache.confirmGroup(group, lambda event: events.append(event))
                        
            for gid in list(self.wifi_networks[fritzbox_ip].keys()):
                if gid not in _active_networks:
                    self.cache.removeGroup(gid, lambda event: events.append(event))
                    del self.wifi_networks[fritzbox_ip][gid]
            
        has_wifi_networks = False
        for _fritzbox_ip in self.config.fritzbox_devices:
            if self.wifi_networks[_fritzbox_ip]:
                has_wifi_networks = True
                break
        self.has_wifi_networks = has_wifi_networks
        # ****************************************************
        
        # ************ Prepare wifi clients ****************
        for node in topologie["nodes"]:
            node_uid = node["uid"]
            mesh_type = node["mesh_role"] if node["is_meshed"] else None
            
            node_macs = [node["device_mac_address"].lower()]
            for node_interface in node["node_interfaces"]:
                node_macs.append(node_interface["mac_address"].lower())
            node_macs = list(set(node_macs))
            
            main_node_mac = None
            for node_mac in node_macs:
                if node_mac in self.dhcp_clients[fritzbox_ip]:
                    main_node_mac = node_mac
                    break
                
            if mesh_type is not None:
                if main_node_mac is None:
                    logging.warning(self.dhcp_clients[fritzbox_ip].keys())
                    logging.warning("No mac found for {} - {}".format(node_uid,node_macs))
                else:
                    mesh_hops[node_uid] = [main_node_mac,mesh_type]
                    
        _active_associations = []
        for node in topologie["nodes"]:
            node_uid = node["uid"]
            
            for node_interface in node["node_interfaces"]:
                if node_interface["type"] != "WLAN":
                    continue

                if node_uid in mesh_hops and node_interface["opmode"] != "REPEATER":
                    continue

                for node_link in node_interface["node_links"]:
                    
                    flip = node_link["node_1_uid"] == node_uid
                    source_key = "node_1_uid" if flip else "node_2_uid"
                    target_key = "node_2_uid" if flip else "node_1_uid"

                    if node_link[target_key] in mesh_hops:
                        source_mac = mesh_hops[node_link[source_key]][0] if node_link[source_key] in mesh_hops else node_interface["mac_address"].lower()
                        target_mac = mesh_hops[node_link[target_key]][0]
                        target_interface = source_mac
                        wifi_network = node_link_wifi_map[node_link["uid"]]
                        vlan = wifi_network["vlan"]
                        band = wifi_network["band"]
                        gid = wifi_network["gid"]
                        
                        device = self.cache.getUnlockedDevice(source_mac)
                        if device is not None:
                            connection_details = { "vlan": vlan, "band": band }
                            
                            device.lock(self)
                            device.cleanDisabledHobConnections(target_mac, lambda event: events.append(event))
                            device.addHopConnection(Connection.WIFI, target_mac, target_interface, connection_details );
                            device.addGID(gid)
                            self.cache.confirmDevice( device, lambda event: events.append(event) )
                            self.wifi_clients[fritzbox_ip][source_mac] = True
                        
                            stat = self.cache.getConnectionStat(target_mac,target_interface)
                            stat_data = stat.getData(connection_details)
                            stat_data.setInSpeed(node_link["cur_data_rate_rx"] * 1000)
                            stat_data.setOutSpeed(node_link["cur_data_rate_tx"] * 1000)
                            stat_data.setDetail("signal", node_link["rx_rcpi"], "attenuation")
                            self.cache.confirmStat( stat, lambda event: events.append(event) )

                        self.wifi_associations[fritzbox_ip][source_mac] = [ source_mac, gid, vlan, target_mac, target_interface ]
                        _active_associations.append(source_mac)
              
        for [ source_mac, gid, vlan, target_mac, target_interface ] in list(self.wifi_associations[fritzbox_ip].values()):
            if source_mac not in _active_associations:
                device = self.cache.getDevice(source_mac)
                device.removeGID(gid);
                # **** connection cleanup and stats cleanup happens in cleanDisabledHobConnection ****
                device.disableHopConnection(Connection.WIFI, target_mac, target_interface)
                self.cache.confirmDevice( device, lambda event: events.append(event) )
                
                del self.wifi_associations[fritzbox_ip][source_mac]
                if source_mac in self.wifi_clients[fritzbox_ip]:
                    del self.wifi_clients[fritzbox_ip][source_mac]
            
        self.cache.unlock(self)
                
    def _fetchDHCPClients(self, fritzbox_ip, events):
        self.next_run[fritzbox_ip]["dhcp_clients"] = datetime.now() + timedelta(seconds=self.config.fritzbox_client_interval)

        first_run = not self.known_clients[fritzbox_ip]

        # collect devices which are not processed or which are outdated
        new_clients = {}
        outdated_clients = {}
        reload_clients = {}
        if not first_run:
            devices = self.cache.getDevices()
            now = datetime.now().timestamp()
            for device in devices:
                mac = device.getMAC()
                if mac not in self.dhcp_clients[fritzbox_ip]:
                    new_clients[mac] = device
                elif now - self.dhcp_clients[fritzbox_ip][mac] >= self.config.fritzbox_network_interval:
                    outdated_clients[mac] = device
                else:
                    continue
                
            reload_clients = outdated_clients.copy()
            for mac in new_clients:
                if mac not in self.known_clients[fritzbox_ip]:
                    reload_clients[mac] = new_clients[mac]
            
        if first_run or reload_clients:
            # check mac is not in known_clients or if known_clients is outdated
            
            start = datetime.now().timestamp()

            # fetch full list
            if first_run or len(reload_clients.keys()) > 5:
                _hosts = {}
                for _host in self.fh[fritzbox_ip].get_generic_host_entries():
                    mac = _host["NewMACAddress"].lower()
                    _hosts[mac] = _host
                self.known_clients[fritzbox_ip] = _hosts
                logging.info("Full refresh in {} seconds".format(datetime.now().timestamp() - start))
            # for small amount of hosts, fetch individual data
            else:
                for mac in reload_clients:
                    try:
                        self.known_clients[fritzbox_ip][mac] = self.fh[fritzbox_ip].get_specific_host_entry(mac.upper())
                    except FritzLookUpError:
                        pass
                logging.info("Partial refresh in {} seconds {}".format(datetime.now().timestamp() - start,list(reload_clients.values())))
                
            hosts = self.known_clients[fritzbox_ip]

            if first_run:
                _hosts = self.known_clients[fritzbox_ip]
                self.fritzbox_macs[fritzbox_ip] = next(mac for mac in _hosts.keys() if _hosts[mac]["NewIPAddress"] == fritzbox_ip )
                logging.info("Found {} for fritzbox {}".format(self.fritzbox_macs[fritzbox_ip], fritzbox_ip))
    
                devices = self.cache.getDevices()
                new_clients = {}
                for device in devices:
                    new_clients[device.getMAC()] = device
           
            obsolete_clients = []
            for device in devices:
                mac = device.getMAC()
                if mac not in hosts and mac in self.dhcp_clients[fritzbox_ip]:
                    obsolete_clients.append(device)

            if new_clients or outdated_clients or obsolete_clients:
                self.cache.lock(self)
                now = datetime.now().timestamp()
                for device in (new_clients | outdated_clients).values():
                    mac = device.getMAC()
                    if mac in hosts:
                        host = hosts[mac]
                        device.lock(self)
                        device.setIP("fritzbox-dhcp", 100, host["NewIPAddress"])
                        device.setDNS("fritzbox-dhcp", 100, host["NewHostName"])
                        self.dhcp_clients[fritzbox_ip][mac] = now
                        self.cache.confirmDevice( device, lambda event: events.append(event) )

                for device in obsolete_clients:
                    logging.info("Removed details from {}".format(device))
                    device.lock(self)
                    device.removeIP("fritzbox-dhcp")
                    device.removeDNS("fritzbox-dhcp")
                    del self.dhcp_clients[fritzbox_ip][mac]
                    self.cache.confirmDevice( device, lambda event: events.append(event) )
                self.cache.unlock(self)
                           
    def _fetchDeviceInfo(self, fritzbox_ip, events):
        self.next_run[fritzbox_ip]["device"] = datetime.now() + timedelta(seconds=self.config.fritzbox_client_interval)

        fritzbox_mac = self.fritzbox_macs[fritzbox_ip]
        
        #https://github.com/blackw1ng/FritzBox-monitor/blob/master/checkfritz.py
        
        #_lan_link_state = self.fc[fritzbox_ip].call_action("LANEthernetInterfaceConfig1", "GetInfo")
        #lan_link_state = {'up': _lan_link_state["NewMaxBitRate"], 'down': _lan_link_state["NewMaxBitRate"], 'duplex': _lan_link_state["NewDuplexMode"]}

        _lan_traffic_state = self.fc[fritzbox_ip].call_action("LANEthernetInterfaceConfig1", "GetStatistics")
        lan_traffic_received = _lan_traffic_state["NewBytesReceived"]
        lan_traffic_sent = _lan_traffic_state["NewBytesSent"]
        
        if fritzbox_mac == self.cache.getGatewayMAC():
            _wan_link_state = self.fc[fritzbox_ip].call_action("WANCommonInterfaceConfig1", "GetCommonLinkProperties")
            wan_link_state = {'type': _wan_link_state["NewWANAccessType"], 'state': _wan_link_state["NewPhysicalLinkStatus"], 'up': _wan_link_state["NewLayer1UpstreamMaxBitRate"], 'down': _wan_link_state["NewLayer1DownstreamMaxBitRate"]}

            _wan_traffic_state = self.fc[fritzbox_ip].call_action("WANCommonIFC1", "GetAddonInfos")
            wan_traffic_state = {'sent': int(_wan_traffic_state["NewX_AVM_DE_TotalBytesSent64"]), 'received': int(_wan_traffic_state["NewX_AVM_DE_TotalBytesReceived64"])}
        
            lan_traffic_received += wan_traffic_state["received"]
            lan_traffic_sent += wan_traffic_state["sent"]

        self.cache.lock(self)

        now = datetime.now()
        
        fritzbox_device = self.cache.getUnlockedDevice(fritzbox_mac)
        if fritzbox_device is None or not fritzbox_device.hasIP("fritzbox"):
            fritzbox_device = self.cache.getDevice(fritzbox_mac)
            fritzbox_device.setIP("fritzbox", 100, fritzbox_ip)
            if fritzbox_mac == self.cache.getGatewayMAC():
                fritzbox_device.addHopConnection(Connection.ETHERNET, self.cache.getWanMAC(), self.cache.getWanInterface() );
            self.cache.confirmDevice( fritzbox_device, lambda event: events.append(event) )
        
        stat = self.cache.getConnectionStat(fritzbox_mac, self.cache.getGatewayInterface(self.config.default_vlan) )
        stat_data = stat.getData() 
        if fritzbox_ip in self.devices:
            time_diff = (now - self.devices[fritzbox_ip]).total_seconds()

            in_bytes = stat_data.getInBytes()
            if in_bytes is not None:
                byte_diff = lan_traffic_received - in_bytes
                if byte_diff > 0:
                    stat_data.setInAvg(byte_diff / time_diff)
                
            out_bytes = stat_data.getOutBytes()
            if out_bytes is not None:
                byte_diff = lan_traffic_sent - out_bytes
                if byte_diff > 0:
                    stat_data.setOutAvg(byte_diff / time_diff)
    
        stat_data.setInBytes(lan_traffic_received)
        stat_data.setOutBytes(lan_traffic_sent)
        #stat_data.setInSpeed(lan_link_state['down'] * 1000)
        stat_data.setInSpeed(1000000000)
        #stat_data.setOutSpeed(lan_link_state['up'] * 1000)
        stat_data.setOutSpeed(1000000000)
        #stat_data.setDetail("duplex", "full" if _port["duplex"] == "fullDuplex" else "half", "string")
        #stat_data.setDetail("duplex", lan_link_state["duplex"], "string")
        self.cache.confirmStat( stat, lambda event: events.append(event) )

        if fritzbox_mac == self.cache.getGatewayMAC():
            stat = self.cache.getConnectionStat(self.cache.getWanMAC(), self.cache.getWanInterface() )
            stat_data = stat.getData()
            stat_data.setDetail("wan_type",wan_link_state["type"], "string")
            stat_data.setDetail("wan_state",wan_link_state["state"], "string")

            if fritzbox_ip in self.devices:
                time_diff = (now - self.devices[fritzbox_ip]).total_seconds()

                in_bytes = stat_data.getInBytes()
                if in_bytes is not None:
                    byte_diff = wan_traffic_state["received"] - in_bytes
                    if byte_diff > 0:
                        stat_data.setInAvg(byte_diff / time_diff)
                    
                out_bytes = stat_data.getOutBytes()
                if out_bytes is not None:
                    byte_diff = wan_traffic_state["sent"] - out_bytes
                    if byte_diff > 0:
                        stat_data.setOutAvg(byte_diff / time_diff)
        
            stat_data.setInBytes(wan_traffic_state["received"])
            stat_data.setOutBytes(wan_traffic_state["sent"])
            stat_data.setInSpeed(wan_link_state["down"] * 1000)
            stat_data.setOutSpeed(wan_link_state["up"] * 1000)
            self.cache.confirmStat( stat, lambda event: events.append(event) )
                
        self.cache.unlock(self)
        
        self.devices[fritzbox_ip] = now

    def _delayedWakeup(self):
        with self.delayed_lock:
            self.delayed_wakeup_timer = None
            
            missing_dhcp_macs = []
            missing_wifi_macs = []
            for mac in list(self.delayed_devices.keys()):
                for fritzbox_ip in self.config.fritzbox_devices:
                    if mac not in self.dhcp_clients[fritzbox_ip]:
                        missing_dhcp_macs.append(mac)
                    if self.has_wifi_networks and mac not in self.wifi_clients[fritzbox_ip] and self.delayed_devices[mac].supportsWifi():
                        missing_wifi_macs.append(mac)
                del self.delayed_devices[mac]
            
            triggered_types = {}
            for fritzbox_ip in self.next_run:
                if len(missing_dhcp_macs) > 0:
                    self.next_run[fritzbox_ip]["dhcp_clients"] = datetime.now()
                    triggered_types["dhcp"] = True
                if len(missing_wifi_macs) > 0:
                    self.next_run[fritzbox_ip]["wifi_clients"] = datetime.now()
                    triggered_types["wifi"] = True
                    
            if triggered_types:
                logging.info("Delayed trigger runs for {}".format(" & ".join(triggered_types)))

                with self.condition:
                    self.condition.notifyAll()
            else:
                logging.info("Delayed trigger not needed anymore")

    def getEventTypes(self):
        return [ 
            { "types": [Event.TYPE_DEVICE], "actions": [Event.ACTION_CREATE], "details": None },
            { "types": [Event.TYPE_DEVICE], "actions": [Event.ACTION_MODIFY], "details": ["online"] }
        ]

    def processEvents(self, events):
        with self.delayed_lock:
            has_new_devices = False
            for event in events:
                device = event.getObject()

                if event.getAction() == Event.ACTION_MODIFY and (not self.has_wifi_networks or not device.supportsWifi()):
                    continue
                
                logging.info("Delayed trigger started for {}".format(device))

                self.delayed_devices[device.getMAC()] = device
                has_new_devices = True

            if has_new_devices:
                if self.delayed_wakeup_timer is not None:
                    self.delayed_wakeup_timer.cancel()

                # delayed triggers try to group several event bulks into one
                self.delayed_wakeup_timer = threading.Timer(5,self._delayedWakeup)
                self.delayed_wakeup_timer.start()
