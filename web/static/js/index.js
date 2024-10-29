let Utils = {};
Utils.getRequest = (name, defaultVal) => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name) || defaultVal;
}

Utils.addComponent = (o, sel) => {
    console.log("COMPONENT LOADED", o, sel);
    sel = sel ? sel : "components";
    $(o).appendTo(sel);
}
var loadedComponents = {};
Utils.loadComponents = (componentList, callback, containerSel) => {
    let promises = [];
    for(let idx in componentList) {
        var componentName = componentList[idx];
        if(!loadedComponents[componentName]) {
            promises.push( $.get('/static/components/'+componentName+'.html', (o) => { Utils.addComponent(o, containerSel) } ) );
            loadedComponents[componentName] = true;
        }
    }
    Promise.all(promises).then(values => {
      console.log("All loaded");
      return callback();
    });
}

let Api = {};
Api.getTaskTypes = (callback) => {
    $.get("/", (o) => {
       console.log("O", o);
    });
}

function renderHome() {
    console.log("Helo");
    const taskTypes = [
        { title:"Adword Analysis/Context generation", image_url:'/static/images/icons/ad_analysis.jpg' },
        { title:"Public Data Analysis", image_url:'/static/images/icons/public_data_analysis.jpg' },
        { title:"Social Media Analysis", image_url:'/static/images/icons/social_media_analysis.jpg' },
        { title:"Survey Data Analysis", image_url:'/static/images/icons/survey_analysis.jpg' },
    ]
    const sel = $("main .tileContainer");
    for(let idx in taskTypes) {
        let taskType = taskTypes[idx];
        let tile = $('.protoTile').clone().removeClass("protoTile");
        for(let key in taskType) {
            const val = taskType[key];
            if(key == 'image_url') {
                tile.find("[data-field="+key+"]").attr('src', val);
            } else {
                tile.find("[data-field="+key+"]").text(val);
            }
        }
        tile.appendTo('.tileContainer');
        //$("<div>HELLO</div>").appendTo(sel);
    }
}


$(document).ready(function() {
    route = Utils.getRequest('route', 'home');
    if(route == 'home') {
        Utils.loadComponents(['tile','tile','tile'], renderHome);
    } else if(route == 'adwords') {
        Utils.loadComponents(['main_adwords'], () => {

        }, '.tileContainer');
    } else if(route == 'public_data') {
        Utils.loadComponents(['main_public_data'], () => {

        }, '.tileContainer');
    } else if(route == 'social_media') {
        Utils.loadComponents(['main_social_media'], () => {

        }, '.tileContainer');
    } else if(route == 'survey') {
        Utils.loadComponents(['main_survey'], () => {

        }, '.tileContainer');
    }
});

