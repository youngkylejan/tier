
var perPage = 6;

var teamNews = $('#team-news-list').children('li');
var num_teamNews = teamNews.size();
var num_newsPages = Math.ceil(num_teamNews / perPage);
var news_curPage = 0;

var teamApplys = $('#team-news-list').children('li');
var num_teamApplys = teamApplys.size();
var num_applysPages = Math.ceil(num_teamApplys / perPage);
var applys_curPage = 0;

function previous(type) {
    var goToPage;

    if (type == 'news') {
        goToPage = parseInt(news_curPage) - 1;
    } else if (type == 'applys') {
        goToPage = parseInt(applys_curPage) - 1;
    }

    if (goToPage >= 0) {
        goTo(goToPage, type);
    }
}

function next(type) {
    var goToPage;
    if (type == 'news') {
        goToPage = parseInt(news_curPage) + 1;
        if (goToPage < num_newsPages) {
            goTo(goToPage, type);
        }
    } else if (type == 'applys') {
        goToPage = parseInt(applys_curPage) + 1;
        if (goToPage < num_applysPages) {
            goTo(goToPage, type);
        }
    }
}

function goTo(page, type){
    var startAt = page * perPage,
        endOn = startAt + perPage;

    if (type == 'news') {
        teamNews.slice(news_curPage * perPage, news_curPage * perPage + perPage).css('display', 'none');
        teamNews.slice(startAt, endOn).css('display', 'block');
        news_curPage = page;
    } else if (type == 'applys') {
        teamApplys.slice(applys_curPage * perPage, applys_curPage * perPage + perPage).css('display', 'none');
        teamApplys.slice(startAt, endOn).css('display', 'block');
        applys_curPage = page;
    }
}

$(document).ready(function() {
    teamNews.css('display', 'none');
    teamNews.slice(news_curPage, perPage).css('display', 'block');

    teamNews.css('display', 'none');
    teamNews.slice(applys_curPage, perPage).css('display', 'block');

    $('#news-previous').click(function(event) {
        previous('news');
    });

    $('#news-next').click(function(event) {
        next('news');
    });

    $('#applys-previous').click(function(event) {
        previous('applys');
    });

    $('#applys-next').click(function(event) {
        next('applys');
    });
});