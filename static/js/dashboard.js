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
  var info = new Object();
  info.type = "post_msg";
  info.team = $('#post-target-team').text();
  info.content = $('#msg-content').val();

  $.ajax({
    url: '/team/news',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
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

function load_team_news(team_name) {
  var info = new Object();
  info.type = "load_news";
  info.team = team_name;

  $.ajax({
    url: '/team/news',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
    },
  })
  .done(function(resp) {
    console.log("success");
    msgs = resp['msgs'];

    $.each(msgs, function(index, msg) {

      var msg_row = $('<div></div>', {class: 'row'});
      var inter_div = $('<div></div>', {class: 'col-md-12'});
      var author_div = $('<small></small>', {class: 'text-muted', text: msg['user'] + " | " + msg['time']});
      var content_text = $('<p></p>', {text: msg['content']});

      inter_div.append(author_div, content_text, "<br/>");
      msg_row.append(inter_div);
      $('#news-board').append(msg_row);

    });
  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
}

function meeting_create() {
  var info = new Object();
  info.type = "create";
  info.team = $('#meeting-target-team').text();
  info.content = $('#meeting-content').val();
  info.time = $('#meeting-time').val();

  $.ajax({
    url: '/team/meetings',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
    },
  })
  .done(function() {
    console.log("success");
  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
};

function load_team_members(team_name) {
  var info = new Object();
  info.team = team_name;

  $.ajax({
    url: '/team/members',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
    },
  })
  .done(function(resp) {
    console.log("success");
    $.each(resp['members'], function(index, member) {
      var li_layout = $('<li></li>', {class: 'assign-member-choice'});
      var a_layout = $('<a></a>', {text: member});
      li_layout.append(a_layout);
      $('#assign-member-dropdown').append(li_layout);
    });
  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
  
};

function create_assignment() {
  var info = new Object();
  info.team = $('#assign-target-team').text();
  info.assignee = $('#assign-target-member').text();
  info.content = $('#assign-content').val();
  info.deadline = $('#assign-deadline').val();

  $.ajax({
    url: '/team/assignments',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
    },
  })
  .done(function() {
    console.log("success");
  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
  
};

function load_meeting_timeline() {
  var info = new Object();
  info.type = "query";
  info.user = $('#nav_user').text();

  $.ajax({
    url: '/team/meetings',
    type: 'POST',
    dataType: 'json',
    data: {
      _xsrf: getCookie("_xsrf"),
      _body: JSON.stringify(info)
    },
  })
  .done(function(resp) {
    console.log("success");

    $.each(resp['meetings'], function(index, meeting) {
      
      var time_icon = $('<i/>', {class: "glyphicon glyphicon-time"});
      var time_small_wrap = $('<small></small>', {class: "text-muted"});
      var time_p_wrap = $('<p/>');
      
      time_small_wrap.append(time_icon);
      time_small_wrap.append(meeting['meeting_time']);
      time_p_wrap.append(time_small_wrap);

      var timeline_team_text = $('<h4/>', {class: 'timeline-title', text: meeting['team']});
      var timeline_heading = $('<div/>', {class: 'timeline-heading'});

      timeline_heading.append(timeline_team_text);
      timeline_heading.append(time_p_wrap);

      var timeline_body_text = $('<p></p>', {text: meeting['content']});
      var timeline_body = $('<div/>', {class: 'timeline-body'});
      timeline_body.append(timeline_body_text);

      var timeline_panel = $('<div/>', {class: 'timeline-panel'});
      timeline_panel.append(timeline_heading);
      timeline_panel.append(timeline_body);

      var timeline_badge = $('<div/>', {class: 'timeline-badge warning'});
      var timeline_badge_icon = $('<i/>', {class: 'glyphicon glyphicon-credit-card'});
      timeline_badge.append(timeline_badge_icon);

      var li_timeline;
      if (index % 2 == 0)
        li_timeline = $('<li/>');
      else
        li_timeline = $('<li/>', {class: "timeline-inverted"});

      li_timeline.append(timeline_badge);
      li_timeline.append(timeline_panel);

      $('#timeline-board').append(li_timeline);
    });

  })
  .fail(function() {
    console.log("error");
  })
  .always(function() {
    console.log("complete");
  });
};

$(document).ready(function() {

  $('.menu-item').click(function(event) {
    var pre_content_id = $('.active').attr('id');
    $('#' + pre_content_id + '-container').attr('style', 'display: None');

    $('.active').removeClass('active');
    $(this).addClass('active');

    var new_content_id = $(this).attr('id');
    $('#' + new_content_id + '-container').attr('style', 'display: Auto');

    if (new_content_id == "meeting-schedule") {
      $('#timeline-board').empty();
      load_meeting_timeline();
    }
  });

  $('.datetimepicker').datetimepicker({ format: 'YYYY-MM-DD HH:mm:ss' });

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
    $('#news-board').empty();
    load_team_news($(this).text());
  });

  // team create
  $('#team-create-clear-btn').click(function(event) {
    $('#team-name-create').val('');
    $('#team-intro-create').val('');
  });

  $('#team-create-confirm-btn').click(function(event) {
    create_team();
  });

  // meeting create
  $('.meeting-team-choice').click(function(event) {
    $('#meeting-target-team').text($(this).text());
  });

  $('#meeting-create-clear-btn').click(function(event) {
    $('#meeting-target-team').text('NONE');
    $('#meeting-content').val('');
    $('#meeting-time').val('');
  });

  $('#meeting-create-confirm-btn').click(function(event) {
    meeting_create();
  });

  // assignment create
  $('.assign-team-choice').click(function(event) {
    $('#assign-target-team').text($(this).text());
    load_team_members($(this).text());
    $('#assign-member-dropdown').empty();
    $('#assign-target-member').text('NONE');
  });

  $('#assign-member-dropdown').on('click', '.assign-member-choice', function(event) {
    event.preventDefault();
    $('#assign-target-member').text($(this).text());
  });

  $('#assign-create-clear-btn').click(function(event) {
    $('#assign-target-team').text('NONE');
    $('#assign-target-member').text('NONE');
    $('#assign-content').val('');
    $('#assign-deadline').val('');
  });

  $('#assign-create-confirm-btn').click(function(event) {
    create_assignment();
  });


});