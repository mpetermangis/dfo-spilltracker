var map = L.map('report_map_leaflet', {
    zoomControl: false
})

L.control.zoom({
    position: 'topright'
}).addTo(map)

// Tile background layers
var esriImagery = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
// var esriBase = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}'
// var mapboxImagery = 'https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw'

L.tileLayer(
    esriImagery, {
    maxZoom: 18,
    attribution: 'Map data &copy; <a href="https://www.esri.com/">ESRI</a>',
    // id: 'mapbox.streets'
}).addTo(map);

// Default view (centered on YVR)
var defaultView = [49.3, -123.5]
var defaultZoom = 11
map.setView(defaultView, defaultZoom)

var spillLyrGroup = L.layerGroup().addTo(map)

function addPoint(report){
    var coord = [report.latitude, report.longitude]
    console.debug('Add point '+coord)
    var marker = new L.CircleMarker(coord)
    // marker.addTo(map)
    marker.bindPopup(report.popup)
    marker.addTo(spillLyrGroup)
}

function clearMarkers(){
    console.log('Clearing markers...')
    spillLyrGroup.clearLayers()
}


var spillSampleRender
function getReportsBbox(){
    var bounds = map.getBounds()
    var bbox = {}
    bbox.lon_min = bounds.getWest()
    bbox.lat_min = bounds.getSouth()
    bbox.lon_max = bounds.getEast()
    bbox.lat_max = bounds.getNorth()
    var bboxStr = JSON.stringify(bbox)
    console.log(`Bbox: ${bboxStr}`)
    // console.log(bbox)

    var mapSearchResults = $.post({
        url: frontendHost + '/report/map_search', 
        // data: JSON.stringify(bbox),
        data: bboxStr,
        dataType: "json",
        contentType: "application/json; charset=utf-8",
    })
    mapSearchResults.done(function(){

        // Clear existing markers
        clearMarkers()

        var spillData = mapSearchResults.responseJSON.data
        console.debug(spillData)
        console.log(`Adding ${spillData.length} spill markers`)
        for (const report of spillData){
            addPoint(report)
        }

        // Display a preview box for the first 5 spills
        var spill5 = spillData.slice(0, 5)
        var spill5Str = JSON.stringify(spill5)
        // Get rendered template from Flask, set HTML content
        // console.log(`Render samples for 5 spills: ${spill5Str}`)
        // var result = 
        var spillSampleData = $.post({
            url: frontendHost + '/report/render_map_samples', 
            // data: JSON.stringify(bbox),
            data: spill5Str,
            dataType: "json",
            contentType: "application/json; charset=utf-8",
        })
        spillSampleData.done(function(){
            $('#reportSample').empty()
            var spillSamples = spillSampleData.responseJSON.data
            // console.log(data)
            console.log(spillSamples)
            // spillSampleRender = data
            $('#reportSample').html(spillSamples)
        })

    })
}

// map.on('zoomend', function() {
map.on('moveend', function() {
    getReportsBbox()
})

$(document).ready(function(){
    console.log('Map is ready.')
    getReportsBbox()
})
