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
            console.log("Adding componentName: ", componentName);
            loadedComponents[componentName] = true;
            promises.push( $.get('/static/components/'+componentName+'.html', (o) => {
                    console.log("Loaded componentName: ", componentName);
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
Api.postJob = (data, callback) => {
    /*
    $.post("/api/v1/job", JSON.stringify(data), (o) => {
       return callback ? callback(o) : null;
    }, 'json');
    */
    $.ajax({
      type: 'POST',
      url: "/api/v1/job",
      data: JSON.stringify(data),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      success: function(data) {
        return callback ? callback(data) : null;
      }
    });
}

function addComponentInstance(sel, componentName, item) {
    //console.log("Add instance", componentName, loadedComponents);
    let componentInstance = loadedComponents[componentName].clone().removeClass("."+componentName)
    //let componentInstance = $('components .'+componentName).clone().removeClass("."+componentName);
    //console.log("Add componentInstance:", componentInstance, " componentName:", componentName)
    for(let key in item) {
        const val = item[key];
        if(key == 'image_url') {
            componentInstance.find("[data-field="+key+"]").attr('src', val);
        } else if(key == 'link') {
            console.log("LINK", val, componentInstance.find("[data-field="+key+"]"));
            componentInstance.find("[data-field="+key+"]").attr('href', val);
        } else {
            componentInstance.find("[data-field="+key+"]").text(val);
            componentInstance.find("[data-attr="+key+"]").attr("data-"+key, val);
        }
    }
    componentInstance.appendTo(sel);
}

let Render = {};
Render.home = () => {
    const taskTypes = [
        { title:"Adword Analysis/Context generation", image_url:'/static/images/icons/ad_analysis.jpg', link:'/static/html/index.html?route=adwords' },
        { title:"Public Data Analysis", image_url:'/static/images/icons/public_data_analysis.jpg', link:'/static/html/index.html?route=public_data' },
        { title:"Social Media Analysis", image_url:'/static/images/icons/social_media_analysis.jpg', link:'/static/html/index.html?route=social_media' },
        { title:"Survey Data Analysis", image_url:'/static/images/icons/survey_analysis.jpg', link:'/static/html/index.html?route=survey' },
    ]
    const sel = $("main .tileContainer");
    for(let idx in taskTypes) {
        let taskType = taskTypes[idx];
        addComponentInstance('.tileContainer', 'tile', taskType);
    }
}

Render.adwords = (data) => {
    const sel = ".main_adwords table tbody";
    $(sel).empty();
    for(idx in data) {
        let item = data[idx];
        console.log("item", item);
        addComponentInstance(sel, 'adwords_row', item);
    }
}
function loadJobs() {
    Api.getQueueJobs('adwords', (o) => {
        console.log("QUEUE", o);
        Render.adwords(o['data']);
    })
}
$(document).ready(function() {
    route = Utils.getRequest('route', 'home');
    if(route == 'home') {
        Utils.loadComponents(['tile'], Render.home);
    } else if(route == 'adwords') {
        Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
            addComponentInstance('.tileContainer', 'main_adwords', {});
            loadJobs();
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

let app = {};
let curDialog = null;

function addJob(obj) {
    let settings = {title:"Add Ad Context Job", width:600};
    curDialog = loadedComponents["adwords_dialog_add_job"];
    $(curDialog).dialog(settings);
}

app.unserializeDialog = function(curDialog, data) {
    curDialog.find("[data-field]").each(function() {
        let el = $(this);
        const key = el.attr('data-field');
        if(data[key] != undefined) {
            el.val(data[key]);
        }
    });
}

app.editJob = function(el) {
    const id = $(el).attr('data-id');
    let settings = {
        title:"Edit Ad Context Job",
        width:600
    }
    let data = {
        id: id,
        title:"ABC",
    }

    curDialog = loadedComponents["adwords_dialog_add_job"];
    app.unserializeDialog(curDialog, data);
    $(curDialog).dialog(settings);
}

function saveJob(el) {
    let mainDialog = $(el).closest(".ui-dialog");
    let data = {};
    let errors = [];
    mainDialog.find("[data-field]").each(function() {
        const key = $(this).attr('data-field');
        const val = $(this).val();
        const minLen = parseInt($(this).attr('data-len-min'));
        data[key] = val;
        if(minLen > 0 && val.length < minLen) {
            errors.push(key+ " must be at least "+minLen+" characters in length")
        }
    });
    console.log(data);
    if(errors.length == 0) {
        Api.postJob(data, () => {
            $(curDialog).dialog('close');
            loadJobs();
        });
    } else {
        alert(errors.join(", "));
    }

}