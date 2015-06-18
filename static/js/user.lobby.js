function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function create_team() {
    var create_info = new Object();
    create_info.name = $('#team-name-create').val();
    create_info.intro = $('#team-intro-create').val();

    $.ajax({
            url: '/team/create',
            type: 'POST',
            dataType: 'json',
            data: {
                _xsrf: getCookie("_xsrf"),
                _create_info: JSON.stringify(create_info)
            },
        })
        .done(function(response) {
            console.log("success");
            if (response['status'] == 'exists')
                alert('team name exists');
        })
        .fail(function() {
            console.log("error");
        })
        .always(function() {
            console.log("complete");
        });
};

$(document).ready(function() {
    // team create
    $('#team-create-clear-btn').click(function(event) {
        $('#team-name-create').val('');
        $('#team-intro-create').val('');
    });

    $('#team-create-confirm-btn').click(function(event) {
        create_team();
    });
});