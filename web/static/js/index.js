let Utils = {};
Utils.get = function(object, path, defaultVal) {
    //console.log(object, path);
    if(typeof window == 'object') {
        window.test = object;
    }
    if(!object) {
        return false;
    }
    if(typeof path == "number") {
        path = "" + path;
    }
    var out = defaultVal;
    var parts = path.split(".");
    var cur = object;
    for(var idx in parts) {
        var pathPart = parts[idx];
        if(typeof cur == "object" && pathPart in cur) {
            cur = cur[pathPart];
        } else {
            return defaultVal;
        }
    }
    if(!cur) {
        cur = defaultVal;
    }
    return cur;
}

Utils.getRequest = (name, defaultVal) => {
  const urlParams = new URLSearchParams(window.location.search);
  if(name != '*') {
      return urlParams.get(name) || defaultVal;
  } else {
      return [...urlParams.entries()].reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {});
  }
}

Utils.objectToReqStr = (obj) => {
    let out = [];
    for(let key in obj) {
        console.log(key, obj[key]);
        if(!obj[key] ||  (typeof obj[key] == 'string' && obj[key].length == 0)) {
            //console.log(" Empty, Skip", !obj[key], );
        } else {
            out.push(key+"="+obj[key]);
        }
    }
    return out.join('&');
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

Utils.titleCase = (str) => {
  return str.toLowerCase().split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
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
Api.getProfile = (callback) => {
    $.get("/api/v1/profile", (o) => {
       return callback(o);
    });
}

Api.getRow = (type, id, callback) => {
    let allParams = Utils.getRequest('*');
    allParams['route'] = null;

    $.get("/api/v1/"+type+"/"+id+"?"+Utils.objectToReqStr(allParams), (o) => {
       return callback(o);
    });
}

Api.getRows = (type, callback) => {
    let allParams = Utils.getRequest('*');
    allParams['route'] = null;

    $.get("/api/v1/"+type+"?"+Utils.objectToReqStr(allParams), (o) => {
       return callback(o);
    });
}
Api.getJob = (id, callback) => {
    $.get("/api/v1/job/"+id, (o) => {
       return callback(o);
    });
}
Api.postRow = (tableName, data, callback) => {
    $.ajax({
      type: 'POST',
      url: "/api/v1/"+tableName,
      data: JSON.stringify(data),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      success: function(data) {
        return callback ? callback(data) : null;
      }
    });
}
Api.putRow = (tableName, id, data, callback) => {
    $.ajax({
      type: 'PUT',
      url: "/api/v1/"+tableName+"/"+id,
      data: JSON.stringify(data),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      success: function(data) {
        return callback ? callback(data) : null;
      }
    });
}

// _________________________ Components  _________________________
Components = {};

function addComponentInstance(sel, componentName, item) {
    //console.log("Add instance", componentName, loadedComponents);
    if(!loadedComponents[componentName]) {
        console.log("Component "+componentName+" not found. Skipping.");
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
            componentInstance.find("[data-field="+key+"]").html(val);
            componentInstance.find("[data-attr="+key+"]").attr("data-"+key, val);
        }
    }
    componentInstance.appendTo(sel);
}
Components.getRowTitles = (rowComponentName) => {
    console.log("getRowTitles", rowComponentName, loadedComponents[rowComponentName]);
    if(!loadedComponents[rowComponentName]) {
        console.log("Component "+rowComponentName+" not found. Skipping.");
        return;
    }
    let rowProto = loadedComponents[rowComponentName];
    let thead = '<tr>';
    $(rowProto).find("[data-field]").each( function() {
         const el = $(this);
         let title = el.attr("data-field");
         if(el.attr("data-title")) {
             title = el.attr("data-title");
         } else {
             title = title.substr(0,1).toUpperCase() + title.substr(1);
         }
         thead += '<th>'+title+'</th>';
         console.log("field", title);
    });
    thead += '</tr>';
    return thead;
}

let app = {};
let curDialog = null;

function addJob(obj) {
    let settings = {title:"Create Ad Context Job", width:600};
    curDialog = loadedComponents["adwords_dialog_add_job"];
    $(curDialog).dialog(settings);
}

app.setWindowTitle = (route) => {
    window.document.title = Utils.titleCase(route.replace(/_/g, ' ')) + " | ReadyAI Organic Query";
}
app.unserializeDialog = function(curDialog, data) {
    curDialog.find("[data-field]").each(function() {
        let el = $(this);
        const key = el.attr('data-field');
        if(data[key] != undefined && data[key] != "") {
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
            Api.putRow('job', data['id'], data, () => {
                $(curDialog).dialog('close');
                app.loadJobs();
            });
        } else {
            Api.postRow('job', data, () => {
                $(curDialog).dialog('close');
                app.loadJobs();
            });
        }
    } else {
        alert(errors.join(", "));
    }

}

app.editPrompt = function(el) {
    const id = $(el).attr('data-id');
    let dialogSettings = {
        title:"Edit Prompt",
        width:600
    }
    Api.getRow('prompt', id, (o) => {
        let data = o['data'];

        curDialog = loadedComponents["dialog/dialog_prompt"];
        app.unserializeDialog(curDialog, data);
        $(curDialog).dialog(dialogSettings);
    });
}

function saveRow(el, tableName) {
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
            Api.putRow(tableName, data['id'], data, () => {
                $(curDialog).dialog('close');
                app.loadJobs();
            });
        } else {
            Api.postRow(tableName, data, () => {
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
app.tableRow = null;
Routes.do = () => {
    Api.getProfile( (o) => {
        if(o['success']) {
            console.log(o);
            let html = Utils.get(o, 'data.username') + " / Credits: <b>" + Utils.get(o, 'data.credits')+"</b>";
            if(true) {
                html += ' | <a style="text-decoration:underline;" href="/static/html/index.html?route=admin">Admin</a>';
            }
            $("#user-info").html(html);
        } else {
            $("#user-info").html("<a href='/login?api_key='>Not logged in</a>");
        }
    });


    route = Utils.getRequest('route', 'home');
    app.setWindowTitle(route);

    if(route == 'home') {
        Utils.loadComponents(['tile'], Render.home);
    } else if(route == 'adwords') {
        jobId = Utils.getRequest('job');
        if(!jobId) {
            Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
                addComponentInstance('.tileContainer', 'main_adwords', {});
                app.tableRow = 'adwords_row';
                app.loadJobs();
                app.loadJobsInterval = setInterval(app.loadJobs.bind(this, true), 5000);
            });
        } else {
            Utils.loadComponents(['main_adwords', 'adwords_row', 'adwords_dialog_add_job'], () => {
                addComponentInstance('.tileContainer', 'job', {});
                app.loadJob(jobId);
            });
        }
    } else if(route == 'adwords_task') {
        jobId = Utils.getRequest('job_id');
        Utils.loadComponents(['main_adwords', 'tasks_row', 'adwords_dialog_add_job'], () => {
            addComponentInstance('.tileContainer', 'main_adwords', {});
            app.tableRow = 'tasks_row';
            app.loadRows('task', Render.adwords, 'tasks_row', true);
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
    } else if(route.substr(0, 5) == 'admin') {
        // TODO: Check user level
        subroute = route.substr(6);
        if(subroute == "prompt_chain") {
            console.log("PC")
            Utils.loadComponents(['main_adwords', 'admin/prompt_chain_row', 'adwords_dialog_add_job'], () => {
                addComponentInstance('.tileContainer', 'main_adwords', {});
                app.tableRow = 'admin/prompt_chain_row';
                app.loadRows('prompt_chain', Render.adwords, app.tableRow, true);
            });
        } else if(subroute == "prompt") {
            Utils.loadComponents(['main_adwords', 'admin/prompt_row', 'dialog/dialog_prompt'], () => {
                addComponentInstance('.tileContainer', 'main_adwords', {});
                app.tableRow = 'admin/prompt_row';
                app.loadRows('prompt', Render.adwords, app.tableRow, true);
            });
        } else {
            Utils.loadComponents(['main_admin'], () => {
                addComponentInstance('.tileContainer', 'main_admin', {});
            });
        }
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

Render.adwords = (data, rowComponentName) => {
    rowComponentName = rowComponentName ? rowComponentName : 'adwords_row';
    console.log("Render.adwords ", data, rowComponentName);
    const sel = ".main_adwords table tbody";
    $(sel).empty();
    const selHead = ".main_adwords table thead";
    $(selHead).empty();
    const rowTitles = Components.getRowTitles(rowComponentName);
    $(rowTitles).appendTo(selHead)

    for(idx in data) {
        let item = data[idx];
        //console.log("adwords render item", item);
        addComponentInstance(sel, rowComponentName, item);
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
            for(idx in o['data']) {
                let item = o['data'][idx];
                item['title_link'] = "<a href='/static/html/index.html?route=adwords_task&job_id="+item['id']+"'>"+item['title']+"</a>";
            }
            Render.adwords(o['data']);
        } else {
            //console.log("No change jobs");
        }
    })
}
app.loadRows = (type, renderFunction, rowComponentName, refreshOnlyOnChange) => {
    Api.getRows(type, (o) => {
        console.log("response", o);
        let change = false;
        let typeVar = 'load_'+type+'_checksum';
        // If endpoint doesn't have a change checksum, always render
        if(!o['checksum']) {
            change = true;
        }
        if(app[typeVar] && app[typeVar] != o['checksum']) {
            change = true;
        }
        app[typeVar] = o['checksum'];
        if( !refreshOnlyOnChange || (refreshOnlyOnChange && change) ) {
            console.log("Refresh "+type);
            return renderFunction(o['data'], rowComponentName);
        } else {
            console.log("No change "+type);
        }
    })
}
app.loadJob = (jobId) => {
    Api.getJob(jobId, (o) => {
        //console.log("QUEUE2", o);
        Render.adwords(o['data']);
    })
}
app.upload = () => {
    const form = document.getElementById('upload-form');
    const filesInput = document.getElementById('files');

    const files = filesInput.files;
    const formData = new FormData();
    const datasetName = $("input[name=dataset-directory]").val();
    formData.append(`dataset_name`, datasetName);

    for (let i = 0; i < files.length; i++) {
        formData.append(`files`, files[i]);
    }

    fetch('/api/v1/upload', {
        method: 'POST',
        body: formData,
        })
          .then((response) => response.json())
          .then((data) => {
              console.log(data);
              $("[data-field=url]").val(datasetName)
          })
          .catch((error) => console.error(error));
}


$(document).ready(function() {
    Routes.do();
});

