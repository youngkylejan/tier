
var perPage = 6;

var teamNews = $('#team-news-list').children('li');
var num_teamNews = teamNews.size();
var num_newsPages = Math.ceil(num_teamNews / perPage);
var news_curPage = 0;

function previous(type) {
    var goToPage;

    if (type == 'news') {
        goToPage = parseInt(news_curPage) - 1;
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
    }
}

function goTo(page, type){
    var startAt = page * perPage,
        endOn = startAt + perPage;

    if (type == 'news') {
        teamNews.slice(news_curPage * perPage, news_curPage * perPage + perPage).css('display', 'none');
        teamNews.slice(startAt, endOn).css('display', 'block');
        news_curPage = page;
    }
}

$(document).ready(function() {
    teamNews.css('display', 'none');
    teamNews.slice(news_curPage, perPage).css('display', 'block');

    $('#news-previous').click(function(event) {
        previous('news');
    });

    $('#news-next').click(function(event) {
        next('news');
    });
});