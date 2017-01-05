function setupJQueryUiWidgets(){
    $("#tabs").tabs();
    $( ".accordion" ).accordion({active: false, collapsible: true, heightStyle: "content"});
    $( ".api_form" ).controlgroup();
}

function serializeObject(obj, prefix){
    var str = [], p;
    for(p in obj) {
        if (obj.hasOwnProperty(p)) {
            var k = prefix ? prefix + "[" + p + "]" : p, v = obj[p];
            str.push((v !== null && typeof v === "object") ?
                serialize(v, k) :
                encodeURIComponent(k) + "=" + encodeURIComponent(v));
        }
    }
    return str.join("&");
}

function loading(form, num_dots, timerID){
    if(! timerID){
        timerID = {"id": 0}
    }
    function update_dots(){
        form.find("pre").text("waiting" + new Array(num_dots+1).join('.'));
        num_dots = (num_dots + 1) % 4;
        if(num_dots == 0){
            num_dots = 1;
        }
        timerID['id'] = setTimeout(update_dots, 1000)
        console.log("timerID: " + timerID['id'])
    }
    timerID['id'] = setTimeout(update_dots, 1000)
    console.log("timerID: " + timerID['id'])
}

function setupFormSubmissionHook(){
    $( ".api_form" ).submit(function(event){
        var form = $(this)
        num_dots = 3
        loading_id = {}
        loading(form, num_dots, loading_id)
        $.ajax({
           type: "GET",
           url: "/api/forward_api?" + serializeObject({
                "url": form.attr('action'),
                "arguments": form.serialize(),
                "method": form.attr('method')
           }),
           crossDomain: true,
           xhrFields:{
            withCredentials: true
           }})
           .done(function(data){
               console.log("Clearing timerID: " + loading_id['id'])
               clearTimeout(loading_id['id'])
               response = JSON.parse(data)

               form.find("pre").text(JSON.stringify(response.result, null, 2));
               form.find('input').each(function(){
                var input = $(this)
                input.attr('value', input.text());
               });
           })
           .fail(function(xhr){
               console.log("Clearing timerID: " + loading_id['id'])
               clearTimeout(loading_id['id'])
               response = JSON.parse(xhr.responseText)

               form.find("pre").text(JSON.stringify(response.result, null, 2));
           });
        event.preventDefault();
   });
}

function drawCharts(){
    for(var key in window.alertData)
    {
        var data = new google.visualization.DataTable();
        data.addColumn('date', 'Time');
        data.addColumn('number', 'Percent');
        data.addColumn('number', 'HIGH TRIGGER VALUE');
        data.addColumn('number', 'LOW TRIGGER VALUE');

        data.addRows(window.alertData[key]['data']);

        var options = {
        width: 900,
        height: 500,
        chartArea: {left:50,  width: 650, height: 400 },
        curveType: 'function',
        series: {
            0: { color: '#20a03e' },
            1: { color: '#ff0000' },
            2: { color: '#ff0000' },
          }
        };
        var chart = new google.visualization.LineChart(document.getElementById("chart"+key));

        chart.draw(data, options);
    }
}

function initPage(){
    setupJQueryUiWidgets();
    setupFormSubmissionHook();
    google.charts.load('current', {packages: ['corechart', 'line']});
    google.charts.setOnLoadCallback(drawCharts);
}



//On Document Ready
$(function() {
   initPage();
});