<?php
require "./shared/libs/ressources.php";
?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#ffffff">
    <link rel="icon" type="image/png" href="/main/img/res/mipmap-mdpi/ic_launcher.png" />
    <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet"> 
    <link href="main/manifest.json" rel="manifest">

    <link href="<?php echo Ressources::getCSSPath('/shared/'); ?>" rel="stylesheet">
    <link href="<?php echo Ressources::getCSSPath('/main/'); ?>" rel="stylesheet">

    <script>var mx = { OnScriptReady: [], OnDocReady: [], Translations: [], User: { 'name': '', 'groups': [], 'memberOf': function(usergroups){ if( typeof usergroups == 'string' ) { usergroups = [usergroups]; }; return usergroups.filter(value => mx.User.groups.includes(value)).length > 0; }  } };<?php
        require "./shared/libs/auth.php";
        echo " mx.User.name = " . json_encode(Auth::getFullname()) . ";";
        echo " mx.User.groups = " . json_encode(Auth::getGroups()) . ";";
    ?></script>
    
    <script src="<?php echo Ressources::getJSPath('/shared/'); ?>"></script>
    <script src="<?php echo Ressources::getJSPath('/main/'); ?>"></script>
    <script src="<?php echo Ressources::getComponentPath('/main/'); ?>"></script>

    <script>
        var demoMode = document.location.search.indexOf("demo=") !== -1;

        var pageReady = false;
        
        var menuPanel = false;
        var visualisationType = "phone";

        var readynessCount = 3; //(background image (scriptready), background image title (scriptready) & initPage (documentready) )

        function initContent()
        {
            readynessCount--;
            if( readynessCount > 0 || !pageReady ) return;

            if( mx.MainImage.getUrl() !== "" )
            {
                mx.$("#background").style.backgroundImage = "url(" + mx.MainImage.getUrl() + ")";
                mx.$("#background").style.opacity = mx.darkLayout ? "0.7" : "1";
            }
            else
            {
                mx.$("body").classList.add("nobackground" );
            }

            var elements = document.querySelectorAll("*[data-i18n]");
            elements.forEach(function(element)
            {
                var key = element.getAttribute("data-i18n");
                element.innerHTML = mx.I18N.get(key);
            });

            mx.Menu.init();

            mx.$('#logo').addEventListener("click",mx.Actions.openHome);

            mx.Actions.init(menuPanel, demoMode);

            var ref = mx.Host.getParameter("ref");

            mx.History.init(function(mainGroup,subGroup,entry,url){
                if( subGroup )
                {
                    if( entry ) mx.Actions.openEntry(entry,url);
                    else mx.Actions.openMenu(subGroup);
                }
                else mx.Actions.openHome();
            });

            mx.Page.checkDeeplink(ref);

            if( !mx.History.getActiveNavigation() ) mx.Actions.openHome();

            mx.$('#page').style.opacity = "1";
        }

        function checkVisualisationType()
        {
            if( window.innerWidth < 600 ) visualisationType = "phone";
            else if( window.innerWidth < 1024 ) visualisationType = "tablet";
            else visualisationType = "desktop";
            
            mx.Actions.setVisualisationType(visualisationType);
            
            menuPanel.enableBackgroundLayer(visualisationType !== "desktop");

            if( visualisationType !== "desktop" )
            {
                mx.$("#side").classList.add("fullsize");
            }
            
            if( visualisationType === "phone" )
            {
                mx.$('body').classList.add('phone');
                mx.$('body').classList.remove('desktop');
            }
            else
            {
                mx.$('body').classList.remove('phone');
                mx.$('body').classList.add('desktop');
            }
            
            mx.Page.initTheme();
        }       
        
        function initPage()
        {
            mx.Page.initInfoLayer();
        
            mx.Swipe.init();
                        
            menuPanel = mx.Panel.init({
                isSwipeable: true,
                enableBackgroundLayer: false,
                selectors: {
                    menuButtons: ".burger.button",
                    panelContainer: '#menu',
                    backgroundLayer: '#layer',
                }
            });

            mx.$('#menu').addEventListener("beforeOpen",function(){
                if( visualisationType == "desktop" ) mx.$("#side").classList.remove("fullsize");
            });
            mx.$('#menu').addEventListener("beforeClose",function(){
                if( visualisationType == "desktop" ) mx.$("#side").classList.add("fullsize");
            });

            mx.$("#layer").addEventListener("click",function()
            {
                menuPanel.close();
            });

            function isPhoneListener(mql){ 
                checkVisualisationType(); 
            }
            var phoneMql = window.matchMedia('(max-width: 600px)');
            phoneMql.addListener(isPhoneListener);
            isPhoneListener(phoneMql);

            var desktopMql = window.matchMedia('(min-width: 1024px)');
            function checkMenu(mql)
            {
                checkVisualisationType();

                if( visualisationType === "desktop" ) 
                {
                    mx.$("#side").classList.remove("fullsize");
                    menuPanel.open();
                }
                else 
                {
                    menuPanel.close();
                }
            }
            desktopMql.addListener(checkMenu);
            checkMenu(desktopMql);

            pageReady = true;
        
            initContent();

            if( mx.User.memberOf("admin") )
            {
                // defined in netdata.js (/components/)
                mx.Alarms.init('.alarm.button','.alarm.button .badge');
            }
            else
            {
                mx.$(".alarm.button").style.display = 'none';
            }
            
            mx.$(".spacer").innerHTML = document.location.hostname;
        }
        
        mx.OnScriptReady.push( function(){
            var imageUrl = "/img/potd/today" + ( mx.Core.isSmartphone() ? "Portrait" : "Landscape") + ".jpg";
            if( demoMode ) imageUrl = "https://images.pexels.com/photos/814499/pexels-photo-814499.jpeg";
            var titleUrl = "/img/potd/todayTitle.txt";
            mx.MainImage.init(imageUrl,titleUrl,initContent);
        });

        mx.OnDocReady.push( initPage );
	</script>
</head>
<body id="app">
<script>
    mx.Page = (function( ret ) {
        ret.initTheme = function()
        {
            var darkMql = window.matchMedia( ( demoMode ? '' : '(prefers-color-scheme: dark) and ' ) + '(max-width: 600px)');
            if( darkMql.matches )
            {
                document.body.classList.add("dark");
            }
            else
            {
                document.body.classList.remove("dark");
            }
            document.cookie = "theme=" + ( darkMql.matches ? "dark" : "light" ) + "; expires=0; domain=" + document.location.hostname;
        };
        
        return ret;
    })( mx.Page || {} );
    
    mx.Page.initTheme();
</script>
<div id="page" style="opacity:0;transition:opacity 300ms linear;">
    <div id="menu" class="c-panel">
        <div class="group">
            <div id="logo" class="button"></div>
            <div class="spacer"></div>
            <div class="alarm button">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path fill="currentColor" d="M433.884 366.059C411.634 343.809 384 316.118 384 208c0-79.394-57.831-145.269-133.663-157.83A31.845 31.845 0 0 0 256 32c0-17.673-14.327-32-32-32s-32 14.327-32 32c0 6.75 2.095 13.008 5.663 18.17C121.831 62.731 64 128.606 64 208c0 108.118-27.643 135.809-49.893 158.059C-16.042 396.208 5.325 448 48.048 448H160c0 35.346 28.654 64 64 64s64-28.654 64-64h111.943c42.638 0 64.151-51.731 33.941-81.941zM224 472a8 8 0 0 1 0 16c-22.056 0-40-17.944-40-40h16c0 13.234 10.766 24 24 24z"></path></svg><span class="badge">0</span>
            </div>
            <div class="burger button">
                <svg style="fill:white;stroke:white;" transform="scale(1.0)" enable-background="new 0 0 91 91" id="Layer_1" version="1.1" viewBox="0 0 91 91" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><g><rect height="3.4" width="39.802" x="27.594" y="31.362"/><rect height="3.4" width="39.802" x="27.594" y="44.962"/><rect height="3.4" width="39.802" x="27.594" y="58.562"/></g></svg>
            </div>
        </div>
        <div class="group" id="menuTemplate" style="display:none">
            <div class="header"></div>
            <div class="service button"><div></div><div></div></div>
        </div>
        <?php
            if( !isset($_SERVER['AUTH_TYPE']) || $_SERVER['AUTH_TYPE'] != "Basic" )
            {
        ?>
        <a class="logout form button" href="/auth/logout/" data-i18n="Logout"></a>
        <?php
            }
        ?>
    </div>
    <div id="side" class="fullsize">
        <div id="header" data-role="header">
            <div class="burger button">
                <svg style="fill:white;stroke:white;" transform="scale(1.0)" enable-background="new 0 0 91 91" id="Layer_1" version="1.1" viewBox="0 0 91 91" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><g><rect height="3.4" width="39.802" x="27.594" y="31.362"/><rect height="3.4" width="39.802" x="27.594" y="44.962"/><rect height="3.4" width="39.802" x="27.594" y="58.562"/></g></svg>
            </div>
            <div class="alarm button">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path fill="currentColor" d="M433.884 366.059C411.634 343.809 384 316.118 384 208c0-79.394-57.831-145.269-133.663-157.83A31.845 31.845 0 0 0 256 32c0-17.673-14.327-32-32-32s-32 14.327-32 32c0 6.75 2.095 13.008 5.663 18.17C121.831 62.731 64 128.606 64 208c0 108.118-27.643 135.809-49.893 158.059C-16.042 396.208 5.325 448 48.048 448H160c0 35.346 28.654 64 64 64s64-28.654 64-64h111.943c42.638 0 64.151-51.731 33.941-81.941zM224 472a8 8 0 0 1 0 16c-22.056 0-40-17.944-40-40h16c0 13.234 10.766 24 24 24z"></path></svg><span class="alarms_count_badge badge">0</span>
            </div>
        </div>
        <div id="content" data-role="main">
            <div id="inline">
                <div id="background"></div>
                <div id="submenu"></div>
            </div>
            <iframe id="embed" src="" frameborder="0" style="display:none"></iframe>
            <div id="embedError" style="display:none">
              <div>
                <div class="head" data-i18n="There was a problem loading the content"></div>
                <div class="info" data-i18n="This can have several reasons"></div>
                <div class="reason">
                  <div>•</div>
                  <div>
                    <div data-i18n="The application to be loaded had a problem."></div>
                    <div data-i18n="You can click <b onclick='mx.Actions.hideErrorLayer()'>'Show anyway'</b> to continue."></div>
                  </div>
                </div>
                <div class="reason">
                  <div>•</div>
                  <div>
                    <div data-i18n="The subdomain's SSL certificate was not accepted."></div>
                    <div data-i18n="Simply click <b onclick='mx.Actions.openFrameInNewWindow()'>'Open in a new window'</b> and confirm the certificate there."></div>
                  </div>
                </div>
                <div class="info" data-i18n="You can now do the following things"></div>
                <div class="actions" ><div class="form button" onClick="mx.Actions.hideErrorLayer()" data-i18n="Show anyway"></div><div class="form button" onClick="mx.Actions.openFrameInNewWindow()" data-i18n="Open in new window"></div></div>
              </div>
            </div>
            <div id="embedProgress" style="display:none">
                <svg x="0px" y="0px" viewBox="0 0 100 100" enable-background="new 0 0 0 0" xml:space="preserve"><use href="#progress" /></svg>
            </div>
        </div>
    </div>
    <div id="layer"></div>
    <div id="info">
        <div>
            <span class="info"></span>
            <span class="hint"></span>
            <span class="progress">
                <svg id="progress" x="0px" y="0px" viewBox="0 0 100 100" enable-background="new 0 0 0 0" xml:space="preserve">
                    <path fill="currentColor" d="M73,50c0-12.7-10.3-23-23-23S27,37.3,27,50 M30.9,50c0-10.5,8.5-19.1,19.1-19.1S69.1,39.5,69.1,50">
                        <animateTransform attributeName="transform" attributeType="XML" type="rotate" dur="1s" from="0 50 50" to="360 50 50" repeatCount="indefinite"></animateTransform>
                    </path>
                </svg>
            </span>
        </div>
    </div>
</div>
</body>
</html>
