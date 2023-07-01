document.body.style.zoom = 1.0;

var form = $('form').on('submit', function (e) {
    e.preventDefault();
    console.log('submitted');
    let orgType = $('select.org_types').val();
    if (orgType === 'sandbox') {
        document.getElementById('linkSand').click();
    } else {
        document.getElementById('linkProd').click();
    }
    var form = $(this);
    var url = '/getOrgType';
    $.ajax({
        type: "POST",
        url: url,
        data: form.serialize(), // serializes the form's elements.
        success: function (data) {
            console.log('success'); // show response from the php script.
        }
    });
});