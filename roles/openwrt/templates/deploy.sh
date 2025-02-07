#!/bin/bash
 
authenticate() {
  N=5
  for i in $(seq 1 $N); do
    if [ -z "$PASSWORD" ]
    then
      echo -n "Enter password": 
      read -s PASSWORD
      echo
    fi
    
    echo -n "Check password ... "
    sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP /bin/true
    
    EXIT_CODE=`echo $?`
    
    if [ "$EXIT_CODE" -eq 6 ]
    then
      echo "unknown key fingerprint."
      echo "Login manually first"
      exit
    elif [ "$EXIT_CODE" -eq 0 ]
    then
      echo "ok"
      break
    else
      unset PASSWORD
    fi
  done
  
  if [ -z "$PASSWORD" ]
  then
    echo "Exit... Got no valid password after $N retries."
    exit
  fi
}

connectivity() {
  N=5
  for i in $(seq 1 $N); do
    if [ -z "$IP" ]
    then
      echo -n "Enter IP adress": 
      read IP
    fi
    
    echo -n "Check connectivity ... "
    ping -c1 -W 1 $IP > /dev/null 2>&1
    if [ $? -eq 0 ]
    then
      echo "ok"
      break
    else
      echo "IP address not reachable"
      unset IP
    fi
  done
  
  if [ -z "$IP" ]
  then
    echo "Exit... Got no valid IP address after $N retries."
    exit
  fi
}

if [[ -n $1 ]]; then
  IP=$1
fi

connectivity

authenticate

SOURCE=`dirname "$0"`
source "$SOURCE/$IP.env"

TZ=`tail -1 "/usr/share/zoneinfo/$TIMEZONE"`

echo "Refresh package lists ..."
sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg update > /dev/null"

if [[ "$INSTALL_PACKAGES" != "" ]]; then
  echo "Install packages ..."
  sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg install" $INSTALL_PACKAGES " > /dev/null"
fi

if [[ "$REMOVE_PACKAGES" != "" ]]; then
  echo "Uninstall packages ..."
  sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg uninstall" $REMOVE_PACKAGES " > /dev/null"
fi

if [[ "$IS_AP" == 1 ]]; then
  echo "Install wifi packages ..."
  sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg remove wpad-basic-wolfssl > /dev/null"
  sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg install wpad-wolfssl hostapd-utils > /dev/null"

  grep "ieee80211r '1'" "$SOURCE/$IP/etc/config/wireless" > /dev/null
  if [ $? -eq 0 ]; then
    echo "Install roaming packages ..."
    sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg install umdns dawn luci-app-dawn > /dev/null"
    sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "[ -f /etc/seccomp/umdns.json ] && mv /etc/seccomp/umdns.json /etc/seccomp/umdns.json.disabled"
  fi
fi

echo "Copy configs ..."
sshpass -f <(printf '%s\n' $PASSWORD) scp -rp $SOURCE/$IP/* root@$IP:/

#authenticate

echo "Apply hostname and timezone ..."
sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "uci set system.cfg01e48a.hostname='$HOSTNAME' & uci commit;"
sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "uci set system.cfg01e48a.zonename='$TIMEZONE'  & uci set system.cfg01e48a.timezone='$TZ' & uci commit;"

echo "Force web redirect ..."
sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "uci set uhttpd.main.redirect_https='on' & uci commit;"

if [[ "$ENABLED_SERVICES" != "" ]]; then
  for SERVICE in "$ENABLED_SERVICES";
  do
    echo "Enable and start $SERVICE ..."
    sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "/etc/init.d/$SERVICE enable & /etc/init.d/$SERVICE start"
  done
fi


#/etc/init.d/rpcd restart
#/etc/init.d/snmpd restart

# disabled upgrades, because they are using too much additional flash space
#echo "Search for upgrades ..."
#AVAILABLE_UPDATES_RESULT=$(sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg list-upgradable")

#if [[ "$AVAILABLE_UPDATES_RESULT" != "" ]]; then
#  AVAILABLE_UPDATES=$(echo "$AVAILABLE_UPDATES_RESULT" | wc -l)
#  echo -n "$AVAILABLE_UPDATES Updates available. Run upgrade packages? [y/N]":
#  read UPGRADE

#  if [[ $UPGRADE =~ ^[Yy]$ ]]; then
#    echo "Upgrading now ..."
#    sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "opkg list-upgradable | cut -f 1 -d ' ' | xargs -r opkg upgrade; > /dev/null"
#  fi
#fi

echo -n "Reboot now? [y/N]": 
read REBOOT
echo

if [[ $REBOOT =~ ^[Yy]$ ]]
then
  echo "Rebooting now ..."
  sshpass -f <(printf '%s\n' $PASSWORD) ssh root@$IP "reboot now"
fi

echo "done"
