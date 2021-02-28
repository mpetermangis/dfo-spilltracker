
// Initialize server-related paths
var host = $(location).attr('hostname')
var protocol = $(location).attr('protocol')
var frontendPort = $(location).attr('port')
var hostbase = protocol+ '//' +host
// Good future-proofing: I put this in here long before upgrading to SSL
var frontendHost = hostbase
if (frontendPort !== 80){
    frontendHost += ':' +frontendPort
}
console.log('Host: '+frontendHost)

// Apply pattern validation for coordinate types
$('#coordinate_type').change(function() {
    var ctype = $('#coordinate_type').val()
    var pattern = null
    var placeholder = null
    if (ctype === 'Decimal Degrees'){
        pattern = '\\d{2}\\.\\d+,-\\d{3}\\.\\d+'
        placeholder = 'XX.XXX,-XXX.XXX'
    } else if (ctype === 'Degrees Decimal Minutes'){
        pattern = "\\d{2} \\d{1,2}\\.\\d+ [Nn] \\d{2,3} \\d{1,2}\\.\\d+ [Ww]"
        placeholder = 'XX XX.XXX N XXX XX.XXX W'
    } else if (ctype === 'Degrees Minutes Seconds'){
        pattern = "\\d{2} \\d{1,2} \\d{1,2} [Nn] \\d{2,3} \\d{1,2} \\d{1,2} [Ww]"
        placeholder = 'XX XX XX N XXX XX XX W'
    } else {
        // Nothing selected, i.e. no coordinates
        pattern = ''
        placeholder = ''
    }
    if ( (pattern) && (placeholder) ){
        console.log(ctype+ ': set pattern: ' + pattern)
        $('#coordinates').attr('pattern', pattern)
        $('#coordinates').attr('placeholder', placeholder)
        $('#coordHelp').html('Format: '+placeholder)
    }
})
