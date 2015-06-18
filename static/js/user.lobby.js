function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function create_team() {
    var info = new Object();
    info.name = $('#team-name-create').val();
    info.intro = $('#team-intro-create').val();

    $.ajax({
            url: '/team/create',
            type: 'POST',
            dataType: 'json',
            data: {
                _xsrf: getCookie("_xsrf"),
                _body: JSON.stringify(info)
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
    wow = new WOW({
        animateClass: 'animated',
        offset: 0
    });
    wow.init();
    
    // team create
    $('#team-create-clear-btn').click(function(event) {
        $('#team-name-create').val('');
        $('#team-intro-create').val('');
    });

    $('#team-create-confirm-btn').click(function(event) {
        create_team();
    });
});