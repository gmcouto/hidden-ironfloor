set sh1 to "launchctl unload -w /Library/LaunchDaemons/info.couto.IronFloor_service.plist;"
set sh2 to "/bin/rm /Library/LaunchDaemons/info.couto.IronFloor_service.plist;"
set sh3 to "/bin/rm /Library/LaunchAgents/info.couto.IronFloor_server.plist;"

set sh to sh1 & sh2 & sh3
do shell script sh with prompt "IronFloor wants to unload daemon" with administrator privileges