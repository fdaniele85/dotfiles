#! /usr/bin/env bash
set -e

action=${1:-status}

status=disabled
if systemctl is-active --quiet vpn.service; then
	status=enabled
fi

if [[ "$action" == "status" ]]; then
	echo "Unina VPN is $status"
	exit 0
fi

if [[ "$action" == "enable" || "$action" == "start" ]]; then
	if [[ $status == "disabled" ]]; then
		sudo /bin/systemctl start vpn.service || exit 1
	fi
	echo "Unina VPN enabled"
	exit 0
fi

if [[ "$action" == "disable" || "$action" == "stop" ]]; then
	sudo /bin/systemctl stop vpn.service
	echo "Disabling Unina VPN"
	exit 0
fi

if [[ "$action" == "switch" ]]; then
	if [[ "$status" == "enabled" ]]; then
		sudo /bin/systemctl stop vpn.service
		echo "Disabling Unina VPN"
		exit 0
	else
		sudo /bin/systemctl start vpn.service
		echo "Enabling Unina VPN"
		exit 0
	fi
fi

exit 1