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

// Layer group for spill points
var spillLyrGroup = L.layerGroup().addTo(map)
const REPORT_SAMPLE_LIMIT = 5
var spillData  // All spill data currently in the map extent

function    addPoint(report){
    var coord = [report.latitude, report.longitude]
    // console.debug('Add point '+coord)
    var marker = new L.CircleMarker(coord, {
        fillColor: '#f03',
        fillOpacity: 0.5,
        weight: 2,
        color: '#f0b5a8'
    })
    // marker.addTo(map)
    marker.bindPopup(report.popup)
    marker.addTo(spillLyrGroup)
}

function clearMarkers(){
    console.log('Clearing markers...')
    spillLyrGroup.clearLayers()
}

function loadNextSpillSamples() {
    // Display a report sample in the right-hand column for the first REPORT_SAMPLE_LIMIT spills
    console.log(`Loading next ${REPORT_SAMPLE_LIMIT} spill samples...`)
    var spillDataLimit = spillData.splice(0, REPORT_SAMPLE_LIMIT)
    if (spillDataLimit.length==0){
        console.log('No more reports to load.')
        $('#loadNextLink').html('No more reports')
    }
    var spillDataStr = JSON.stringify(spillDataLimit)
    // Get rendered template from Flask, set HTML content
    var spillDataPost = $.post({
        url: frontendHost + '/report/render_map_samples', 
        data: spillDataStr,
        dataType: "json",
        contentType: "application/json; charset=utf-8",
    })
    spillDataPost.done(function(){
        
        var spillDataRendered = spillDataPost.responseJSON.data
        $('#report_map_samples').append(spillDataRendered)
    })
}


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

        spillData = mapSearchResults.responseJSON.data
        // console.debug(spillData)
        console.log(`Adding ${spillData.length} spill markers`)
        for (const report of spillData){
            addPoint(report)
        }

        loadNextSpillSamples()

        // Display a report sample in the right-hand column for the first REPORT_SAMPLE_LIMIT spills
        // var spillDataLimit = spillData.slice(0, REPORT_SAMPLE_LIMIT)
        // var spillDataStr = JSON.stringify(spillDataLimit)
        // // Get rendered template from Flask, set HTML content
        // var spillDataPost = $.post({
        //     url: frontendHost + '/report/render_map_samples', 
        //     // data: JSON.stringify(bbox),
        //     data: spillDataStr,
        //     dataType: "json",
        //     contentType: "application/json; charset=utf-8",
        // })
        // spillDataPost.done(function(){
        //     $('#report_map_samples').empty()
        //     var spillDataRendered = spillDataPost.responseJSON.data
        //     // console.log(data)
        //     console.log(spillDataRendered)
        //     // spillSampleRender = data
        //     $('#report_map_samples').html(spillDataRendered)
        // })

    })
}

$('#loadNextSamples').on('click', function(){
    loadNextSpillSamples()
})

// map.on('zoomend', function() {
map.on('moveend', function() {
    // Map view has changed, need to clear the spill samples
    $('#report_map_samples').empty()
    $('#loadNextLink').html('Load More...')
    getReportsBbox()
})

$(document).ready(function(){
    console.log('Map is ready.')
    getReportsBbox()
})
