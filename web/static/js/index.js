let Utils = {};
Utils.getRequest = (name, defaultVal) => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name) || defaultVal;
}

Utils.addComponent = (o, sel, componentName) => {
    console.log("COMPONENT LOADED", o, sel, componentName);
    sel = sel ? sel : "components";
    loadedComponents[componentName] = $(o);

    //$(o).appendTo(sel);
}
var loadedComponents = {};
Utils.loadComponents = (componentList, callback, containerSel) => {
    let promises = [];
    for(let idx in componentList) {
        const componentName = componentList[idx];
        if(!loadedComponents[componentName]) {
            console.log("componentName", componentName);
            loadedComponents[componentName] = true;
            promises.push( $.get('/static/components/'+componentName+'.html', (o) => {
                    console.log("componentName2", componentName);
                Utils.addComponent(o, containerSel, componentName)
            } ) );
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
    console.log("Add instance", componentName, loadedComponents);
    let componentInstance = loadedComponents[componentName].clone().removeClass("."+componentName)
    //let componentInstance = $('components .'+componentName).clone().removeClass("."+componentName);
    console.log("componentInstance", componentInstance, 'components .'+componentName)
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
        console.log("item", item);
        addComponentInstance(sel, 'adwords_row', item);
    }
}

$(document).ready(function() {
    route = Utils.getRequest('route', 'home');
    if(route == 'home') {
        Utils.loadComponents(['tile','tile','tile'], Render.home);
    } else if(route == 'adwords') {
        Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
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

function addJob(obj) {
    $(loadedComponents["adwords_dialog_add_job"]).dialog({title:"Add Ad Context Job", width:600});
}
