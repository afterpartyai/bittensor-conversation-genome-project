let Utils = {};
Utils.getRequest = (name, defaultVal) => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name) || defaultVal;
}

Utils.addComponent = (o, sel, componentName) => {
    //console.log("COMPONENT LOADED", o, sel, componentName);
    sel = sel ? sel : "components";
    loadedComponents[componentName] = $(o);
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
Utils.statsStrs = {
    1: {title: "Active", color:"black", },
    2: {title: "Preprocessed", color:"orange", },
    3: {title: "Complete", color:"green", },
    4: {title: "Four", color:"black", },
    5: {title: "Five", color:"black", },
    14: {title: "Other", color:"black", },
    90: {title: "Error", color:"red", },
    91: {title: "Error", color:"red", },
    92: {title: "Error", color:"red", },
    93: {title: "Error", color:"red", },
    94: {title: "Error", color:"red", },
    95: {title: "Error", color:"red", },
}
Utils.statusToStr = (num, styled) => {
    let val = num;
    if(Utils.statsStrs[num]) {
        val = Utils.statsStrs[num]['title'];
        if(true || styled) {
            val = '<span title="Status: '+num+'" style="color:'+Utils.statsStrs[num]['color']+';">'+val+'</span>';
        }
    }

    return val;
}

// _________________________ API Calls  _________________________

let Api = {};
Api.getTaskTypes = (callback) => {
    $.get("/", (o) => {
       console.log("O", o);
    });
}
Api.getJobs = (type, callback) => {
    $.get("/api/v1/job", (o) => {
       return callback(o);
    });
}
Api.getJob = (id, callback) => {
    $.get("/api/v1/job/"+id, (o) => {
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
Api.putJob = (id, data, callback) => {
    $.ajax({
      type: 'PUT',
      url: "/api/v1/job/"+id,
      data: JSON.stringify(data),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      success: function(data) {
        return callback ? callback(data) : null;
      }
    });
}

// _________________________ Components  _________________________

function addComponentInstance(sel, componentName, item) {
    //console.log("Add instance", componentName, loadedComponents);
    if(!loadedComponents[componentName]) {
        console.log("Component "+componentName+" not found. Aborting");
        return;
    }
    let componentInstance = loadedComponents[componentName].clone().removeClass("."+componentName)
    //let componentInstance = $('components .'+componentName).clone().removeClass("."+componentName);
    //console.log("Add componentInstance:", componentInstance, " componentName:", componentName)
    for(let key in item) {
        const val = item[key];
        if(key == 'image_url') {
            componentInstance.find("[data-field="+key+"]").attr('src', val);
        } else if(key == 'status') {
            componentInstance.find("[data-field="+key+"]").html(Utils.statusToStr(val), true);
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

let app = {};
let curDialog = null;

function addJob(obj) {
    let settings = {title:"Create Ad Context Job", width:600};
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
    let dialogSettings = {
        title:"Edit Ad Context Job",
        width:600
    }
    Api.getJob(id, (o) => {
        let data = o['data'];

        curDialog = loadedComponents["adwords_dialog_add_job"];
        app.unserializeDialog(curDialog, data);
        $(curDialog).dialog(dialogSettings);
    });
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
        if(data['id']) {
            Api.putJob(data['id'], data, () => {
                $(curDialog).dialog('close');
                app.loadJobs();
            });
        } else {
            Api.postJob(data, () => {
                $(curDialog).dialog('close');
                app.loadJobs();
            });
        }
    } else {
        alert(errors.join(", "));
    }

}

// _________________________ Routes _________________________

let Routes = {};

Routes.do = () => {
    route = Utils.getRequest('route', 'home');
    jobId = Utils.getRequest('job');

    if(route == 'home') {
        Utils.loadComponents(['tile'], Render.home);
    } else if(route == 'adwords') {
        if(!jobId) {
            Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
                addComponentInstance('.tileContainer', 'main_adwords', {});
                app.loadJobs();
                app.loadJobsInterval = setInterval(app.loadJobs.bind(this, true), 5000);
            });
        } else {
            Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
                addComponentInstance('.tileContainer', 'job', {});
                app.loadJob(jobId);
            });
        }
    } else if(route == 'public_data') {
        Utils.loadComponents(['main_public_data'], () => {

        }, '.tileContainer');
    } else if(route == 'social_media') {
        Utils.loadComponents(['main_social_media'], () => {

        }, '.tileContainer');
    } else if(route == 'survey') {
        Utils.loadComponents(['main_survey'], () => {

        }, '.tileContainer');
    } else if(route == 'admin') {
        Utils.loadComponents(['main_admin'], () => {
            addComponentInstance('.tileContainer', 'main_admin', {});
        });
    }
}

// _________________________ Renderers _________________________

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
        //console.log("adwords render item", item);
        addComponentInstance(sel, 'adwords_row', item);
    }
}
app.loadJobs = (refreshOnlyOnChange) => {
    Api.getJobs('adwords', (o) => {
        let change = false;
        if(app['loadJobsChecksum'] && app['loadJobsChecksum'] != o['checksum']) {
            change = true;
        }
        app['loadJobsChecksum'] = o['checksum'];
        //console.log("QUEUE1", o);
        if( !refreshOnlyOnChange || (refreshOnlyOnChange && change) ) {
            console.log("Refresh jobs");
            Render.adwords(o['data']);
        } else {
            //console.log("No change jobs");
        }
    })
}
app.loadJob = (jobId) => {
    Api.getJob(jobId, (o) => {
        //console.log("QUEUE2", o);
        Render.adwords(o['data']);
    })
}

$(document).ready(function() {
    Routes.do();
});

