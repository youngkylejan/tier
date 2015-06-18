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
            if (response['status'] == 'exists') {
                $('#failed-create-btn').fadeIn('400', function() {
                    $('#failed-create-btn').delay(1000).fadeOut('400');
                });
            } else {
                $('#success-create-btn').fadeIn('400', function() {
                    $('#success-create-btn').delay(1000).fadeOut('400');
                });
            }

        })
        .fail(function() {
            console.log("error");
        })
        .always(function() {
            console.log("complete");
        });
};

var perPage = 6;

var joinedTeams = $('#joined-team-list').children('li');
var num_JoinedTeams = joinedTeams.children().size();
var num_JoinedPages = Math.ceil(num_JoinedTeams / perPage);
var joined_CurPage = 0;

var remainedTeams = $('#remained-team-list').children('li');
var num_RemainedTeams = remainedTeams.children().size();
var num_RemainedPages = Math.ceil(num_RemainedTeams / perPage);
var remained_CurPage = 0;

joinedTeams.children('li').css('display', 'none');
joinedTeams.children('li').slice(0, perPage).css('display', 'block');

remainedTeams.children('li').css('display', 'none');
remainedTeams.children('li').slice(0, perPage).css('display', 'block');

function previous(type) {
    var goToPage;
    if (type == 'joined') {
        goToPage = parseInt(joined_CurPage) - 1;
    } else {
        goToPage = parseInt(remained_CurPage) - 1;
    }

    if (goToPage >= 0) {
        goTo(goToPage);
    }
}

function next(type) {
    var goToPage;
    if (type == 'joined') {
        goToPage = parseInt(joined_CurPage) + 1;
        if (goToPage < num_JoinedPages)
            goTo(goToPage);
    } else {
        goToPage = parseInt(remained_CurPage) + 1;
        if (goToPage < num_RemainedPages)
            goTo(goToPage);
    }
}

function goTo(page, type){
    var startAt = page * perPage,
        endOn = startAt + perPage;

    if (type == 'joined') {
        joinedTeams.children().css('display', 'none').slice(startAt, endOn).css('display', 'block');
        joined_CurPage = page;
    } else {
        remainedTeams.children().css('display', 'none').slice(startAt, endOn).css('display', 'block');
        remained_CurPage = page;    
    }
}

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

    // paging
    $('#joined-previous').click(function(event) {
        previous('joined');
    });

    $('#joined-next').click(function(event) {
        next('joined');
    });

    $('#remained-previous').click(function(event) {
        previous('remained');
    });

    $('#remained-next').click(function(event) {
        next('remained');
    });
});