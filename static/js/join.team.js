function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function join_team_apply(action) {
    var info = new Object();
    info.user_name = $('#nav_user').text();
    info.team_name = $('#team_name').text();
    info.action = action

    $.ajax({
            url: '/team/join',
            type: 'POST',
            dataType: 'json',
            data: {
                _xsrf: getCookie("_xsrf"),
                _body: JSON.stringify(info)
            },
        })
        .done(function(response) {
            console.log("success");
            if (response['status'] == 'applys') {
                $('#join-team-btn').text('Applys Submitted, wating for processing!');
                $('#join-team-btn').attr('disabled', 'disabled');
            } else if (response['status'] == 'exists') {
                $('#join-team-btn').text('Joined!');
                $('#join-team-btn').attr('disabled', 'disabled');
            }
        })
        .fail(function() {
            console.log("error");
        })
        .always(function() {
            console.log("complete");
        });
};

$(document).ready(function() {
    join_team_apply('check');

    $('#join-team-btn').click(function() {
        join_team_apply('apply');
    });

});