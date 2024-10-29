function displayTaskTypes() {
    console.log("Helo");
    const taskTypes = [
        { title:"A", image_url:'/static/images/icons/ad_analysis.jpg' },
        { title:"B", image_url:'/static/images/icons/public_data_analysis.jpg' },
        { title:"C", image_url:'/static/images/icons/social_media_analysis.jpg' },
        { title:"D", image_url:'/static/images/icons/survey_analysis.jpg' },
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
    displayTaskTypes();
});

