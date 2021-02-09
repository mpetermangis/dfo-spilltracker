
var mymap = L.map('mapid', {
    zoomControl: false
})

// Default view (Canada-wide)
var defaultView = [55.0, -90.5]
var defaultZoom = 4
mymap.setView(defaultView, defaultZoom)
L.control.zoom({
    position: 'topright'
}).addTo(mymap)

// Default marker, draggable
var coordCenter = [0, 0]
// var marker = new L.CircleMarker(coordCenter, {draggable:'true'})
// Use marker, NOT CircleMarker (which is not draggable)
// https://leafletjs.com/reference-1.7.1.html#marker
var marker = L.marker(coordCenter, {draggable:'true'})

// Check if saved_* vars have been initialized
if ( (typeof(saved_latitude) != "undefined") && (typeof(saved_longitude) != "undefined") ){
    if ( (Number.isFinite(saved_latitude)) && (Number.isFinite(saved_longitude))){
        console.log('Report has lat-lon. Initialize map at '+saved_latitude+','+saved_longitude)
        coordCenter = [saved_latitude, saved_longitude]
        marker.setLatLng(coordCenter)
        mymap.setView(coordCenter, 8)
    }
}

// TODO: cache current coordinates here
var coordType
var coordText
var coordData

function refreshCoords(){
    /**
     * Function called whenever coordinates are refreshed by any of the following:
     * 1. (re)loading the report_form page
     * 2. moving the marker on the map
     * 3. changing the coordinate display type
     *  */ 
    
}


// Bind dragend event
marker.on('dragend', function(event){
    // var marker = event.target;
    var position = marker.getLatLng();
    // var loc = new L.LatLng(position.lat, position.lng)
    marker.setLatLng(position, {draggable: 'true'});
    // mymap.panTo(new L.LatLng(position.lat, position.lng))
    // TODO: Update coordinate form fields from latlon
    // var data = {}
    // data.latitude = position.lat
    // data.coordinate_type = position.lng

    var jsonData = JSON.stringify(position)
    console.log('Sending marker position from map: ' +jsonData)
    var result = $.post({
        url: frontendHost + '/latlon_to_coords', 
        data: jsonData,
        dataType: "json",
        contentType: "application/json; charset=utf-8",
    })
    result.done(function(){
        console.log('Coordinates sent for validation.')
        var data = result.responseJSON.data
        console.log(data)
        var coordType = $('#coordinate_type').val()
        // Set value of coordinate field from returned coordinates
        $('#coordinates').val(data[coordType])
    })

})

// Must also enable dragging: 
// marker.dragging.enable();
marker.addTo(mymap)
marker.dragging.enable();


// Tile background layers
var esriImagery = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
// var esriBase = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}'
// var mapboxImagery = 'https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw'



L.tileLayer(
    esriImagery, {
    maxZoom: 18,
    attribution: 'Map data &copy; <a href="https://www.esri.com/">ESRI</a>',
    id: 'mapbox.streets'
}).addTo(mymap);

// Validate coordinates on change
$('#coordinates').change( function() {
    var data = {}
    data.coord_str = $('#coordinates').val()
    data.coordinate_type = $('#coordinate_type').val()

    console.log('Sending: ' +jdata)
    var result = $.post({
        url: frontendHost + '/chk_coordinates', 
        data: JSON.stringify(data),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
    })
    result.done(function(){
        console.log('Coordinates sent for validation.')
        // Hide error text if exists
        $('#coord_error').addClass('d-none')
        var data = result.responseJSON.data
        $('#latitude_calc').html(data.lat)
        $('#latitude').val(data.lat)
        $('#longitude_calc').html(data.lon)
        $('#longitude').val(data.lon)
        console.log(result.responseJSON)
        // Add coordinate on map
        // marker = new L.CircleMarker([data.lat, data.lon])
        coordCenter = [data.lat, data.lon]
        marker.setLatLng(coordCenter, {draggable: 'true'})
        // marker.addTo(mymap)
        mymap.setView(coordCenter, 8)
    })
    result.fail(function(xhr, status, error) {
        var errmsg = result.responseJSON.msg
        console.log(errmsg)
        $('#coord_error').html(errmsg)
        $('#coord_error').removeClass('d-none')
    }) 
})
