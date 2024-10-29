let Utils = {};
Utils.getRequest = (name, defaultVal) => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name) || defaultVal;
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
        renderHome();
    }
});

