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
      _xsrf : getCookie("_xsrf"),
      _create_info : JSON.stringify(create_info)
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

function post_msg() {
  var new_info = new Object();
  new_info.team = $('#post-target-team').text();
  new_info.content = $('#msg-content').val();

  $.ajax({
    url: '/team/news',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _new_info: JSON.stringify(new_info)
    },
  })
  .done(function(resp) {
    console.log("success");
  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
  
};

function load_msg() {
  var load_news_info = new Object();
}

$(document).ready(function() {

  $('.menu-item').click(function(event) {
    var pre_content_id = $('.active').attr('id');
    $('#' + pre_content_id + '-container').attr('style', 'display: None');

    $('.active').removeClass('active');
    $(this).addClass('active');

    var new_content_id = $(this).attr('id');
    $('#' + new_content_id + '-container').attr('style', 'display: Auto');
  });

  $('#datetimepicker1').datetimepicker({
    format: 'YYYY-MM-DD'
  });

  // msg post
  $('.post-team-choice').click(function(event) {
    $('#post-target-team').text($(this).text());
  });

  $('#msg-post-clear-btn').click(function(event) {
    $('#post-target-team').text('NONE');
    $('#msg-content').val('');
  });

  $('#msg-post-confirm-btn').click(function(event) {
    post_msg();
  });

  // news team load
  $('.load-team-choice').click(function(event) {
    $('#load-target-team').text($(this).text());
  });

  // team create
  $('#team-create-clear-btn').click(function(event) {
    $('#team-name-create').val('');
    $('#team-intro-create').val('');
  });

  $('#team-create-confirm-btn').click(function(event) {
    create_team();
  });
});