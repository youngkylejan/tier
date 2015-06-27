function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function join_team_apply(action) {
    $.ajax({
            url: '/team/join',
            type: 'POST',
            dataType: 'json',
            data: {
                _xsrf: getCookie("_xsrf"),
                _name: $('#team_name').text(),
                _action: action
            },
        })
        .done(function(response) {
            console.log("success");
            if (response['status'] == 'exists' || response['status'] == 'applys') {
                $('#join_button').text('Applys Submitted, wating for processing!');
                $('#join_button').attr('disabled', 'disabled');
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