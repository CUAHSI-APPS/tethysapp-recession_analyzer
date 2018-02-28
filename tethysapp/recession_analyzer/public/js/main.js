// var jsonString = "{{ gage_json }}".replace(/&quot;/g, "\"");
//         var workingJson = JSON.parse(jsonString);
//         setGages(workingJson);
//         updatePlots(gages[0]);
//     var gages = [];

    function showValue(newValue, rangex) {
        document.getElementById(rangex).innerHTML=newValue;
    }

    function setGages(gagesArray) {
        gages = gagesArray;
    }

    function filename() {
        return "{{ abJson }}".toJSON()
    }

    function updateSeries(currGage, type) {
        for (i = 0; i < gages.length; i++) {
            var x = document.getElementById(type + gages[i]);
            x.style.visibility = 'hidden';
            x.style.display = 'none';
        }
        var y = document.getElementById(type + currGage);
        y.style.visibility = 'visible';
        y.style.display = 'block';
    }

    function updatePlots(gage) {
        updateSeries(gage, 'plot');
        updateSeries(gage, 'AB');
        updateSeries(gage, 'table');
    }