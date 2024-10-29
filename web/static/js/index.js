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
Api.getQueueJobs = (type, callback) => {
    $.get("/api/v1/queue", (o) => {
       return callback(o);
    });
}

function addComponentInstance(sel, componentName, item) {
    let componentInstance = $('components .'+componentName).clone().removeClass("."+componentName);
    for(let key in item) {
        const val = item[key];
        if(key == 'image_url') {
            componentInstance.find("[data-field="+key+"]").attr('src', val);
        } else {
            componentInstance.find("[data-field="+key+"]").text(val);
        }
    }
    componentInstance.appendTo(sel);
}
let Render = {};
Render.home = () => {
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
    }
}

Render.adwords = (data) => {
    const sel = ".main_adwords table tbody";
    for(idx in data) {
        let item = data[idx];
        addComponentInstance(sel, 'adword_row', item);
        console.log("item", item);
    }
}

$(document).ready(function() {
    route = Utils.getRequest('route', 'home');
    if(route == 'home') {
        Utils.loadComponents(['tile','tile','tile'], Render.home);
    } else if(route == 'adwords') {
        Utils.loadComponents(['main_adwords', 'adwords_row'], () => {
            addComponentInstance('.tileContainer', 'main_adwords', {});
            Api.getQueueJobs('adwords', (o) => {
                console.log("QUEUE", o);
                Render.adwords(o['data']);
            })
        });
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

