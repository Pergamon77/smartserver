mx.Menu.getMainGroup('administration').getSubGroup('states').addUrl(300, 'url', '//netdata.{host}/', '{i18n_State}', '{i18n_Netdata}', false);

mx.Alarms = (function( ret ) {
    var buttonSelector;
    var counterSelector;
    var alarmIsWorking = true;

    function handleAlarms(data) 
    {
        var warnCount = 0;
        var errorCount = 0;

        for(x in data.alarms) 
        {
            if(!data.alarms.hasOwnProperty(x)) continue;

            var alarm = data.alarms[x];
            if(alarm.status === 'WARNING')
            {
                warnCount++;
            }
            if(alarm.status === 'CRITICAL')
            {
                errorCount++;
            }
        }

        mx.$$(counterSelector).forEach(function(element){ element.innerText = warnCount + errorCount });

        var badgeButtons = mx.$$(buttonSelector);
        if( warnCount > 0 )
        {
            badgeButtons.forEach(function(element){ element.classList.add("warn") });
        }
        else
        {
            badgeButtons.forEach(function(element){ element.classList.remove("warn") });
        }
        if( errorCount > 0 )
        {
            badgeButtons.forEach(function(element){ element.classList.add("error") });
        }
        else
        {
            badgeButtons.forEach(function(element){ element.classList.remove("error") });
        }
    }            

    function loadAlerts()
    {
        var id = Math.round( Date.now() / 1000 );

        var xhr = new XMLHttpRequest();
        xhr.open("GET", "//" + mx.Host.getAuthType() + "netdata." + mx.Host.getDomain() + "/api/v1/alarms?active&_=" + id);
        xhr.withCredentials = true;
        xhr.onreadystatechange = function() {
            if (this.readyState != 4) return;

            if( this.status == 200 )
            {
                if( !alarmIsWorking )
                {
                    mx.$$(buttonSelector).forEach(function(element){ element.classList.remove("disabled") });
                    alarmIsWorking = true;
                }
                handleAlarms( JSON.parse(this.response) );
            }
            else if( alarmIsWorking )
            {
                mx.$$(buttonSelector).forEach(function(element){ element.classList.add("disabled") });
                alarmIsWorking = false;
            }
            // must be 10000, because the apache KeepAlive timeout is 15 seconds. 
            // Otherwise, the https connection is established again and again and will take ~700ms instead of 40ms 
            window.setTimeout(loadAlerts,10000);
        };
        xhr.send();
    }

    ret.init = function(_buttonSelector,_counterSelector)
    {
        buttonSelector = _buttonSelector;
        counterSelector = _counterSelector;
        
        mx.$$(buttonSelector).forEach(function(element){ 
            element.addEventListener("click",function()
            {
                mx.Actions.openUrl(null,null,"//" + mx.Host.getAuthType() + "netdata." + mx.Host.getDomain(),false);
            });
        });
        loadAlerts();
    }

    return ret;
})( mx.Alarms || {} );