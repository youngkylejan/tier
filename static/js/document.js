var clientId = '873409246400-kt0n34ibcgtflie4hta97gnvvuqf27sq.apps.googleusercontent.com';

if (!/^([0-9])$/.test(clientId[0])) {
    alert('Invalid Client ID - did you forget to insert your application Client ID?');
}
// Create a new instance of the realtime utility with your client ID.
var realtimeUtils = new utils.RealtimeUtils({ clientId: clientId });

// The first time a file is opened, it must be initialized with the
// document structure. This function will add a collaborative string
// to our model at the root.
function onFileInitialize(model) {
    var string = model.createString();
    string.setText('');
    model.getRoot().set('demo_string', string);
}

// After a file has been initialized and loaded, we can access the
// document. We will wire up the data model to the UI.
function onFileLoaded(doc) {
    var collaborativeString = doc.getModel().getRoot().get('demo_string');
    wireTextBoxes(collaborativeString);
}

// Connects the text boxes to the collaborative string
function wireTextBoxes(collaborativeString) {
    var textArea1 = document.getElementById('text');
    gapi.drive.realtime.databinding.bindString(collaborativeString, textArea1);
}

function create_doc() {

    realtimeUtils.authorize(function(response){
        if(response.error){
            realtimeUtils.authorize(function(response){
                createDocument();
                console.log("YES");
            }, true);
        } else {
            createDocument();
            console.log("NO");
        }
    }, false);
}

function createDocument() {

    var doc = $('#doc-name-create').val().toString();

    if(doc == "")return;

    var info = new Object();
    info.team = $('#team-name').text();
    info.document_name = doc;

    realtimeUtils.createRealtimeFile(doc, function(createResponse) {
        info.document_id = createResponse.id.toString();
        console.log(info);
        $.ajax({
            url: '/team/document',
            type: 'POST',
            dataType: 'json',
            data: {
                _xsrf: getCookie("_xsrf"),
                _body: JSON.stringify(info)
            },
        })
        .done(function(resp) {
            console.log("success");
            $('#doc-success-btn').fadeIn('400', function() {
                $('#doc-success-btn').delay(1000).fadeOut('400');
            });
        })
        .fail(function() {
            console.log("error");
        })
        .always(function() {
            console.log("complete");
        });
    });
}

function load_doc(id) {

    document.getElementById('edit-doc').style.display = 'block';
    document.getElementById('doc-management').style.display = 'none';

    realtimeUtils.authorize(function(response){
        if(response.error){
            realtimeUtils.authorize(function(response){
                realtimeUtils.load(id, onFileLoaded, onFileInitialize);
                console.log("YES");
            }, true);
        } else {
            realtimeUtils.load(id, onFileLoaded, onFileInitialize);
            console.log("NO");
        }
    }, false);
}

function back_doc() {

    document.getElementById('edit-doc').style.display = 'none';
    document.getElementById('doc-management').style.display = 'block';
}

function save_doc() {
    var textToWrite = $('#text').val();
    var textFileAsBlob = new Blob([textToWrite], {type:'text/plain'});
    var fileNameToSaveAs = $('#team-name').text();

    var downloadLink = document.createElement("a");
    downloadLink.download = fileNameToSaveAs;
    downloadLink.innerHTML = "Download File";
    if (window.webkitURL != null)
    {
        // Chrome allows the link to be clicked
        // without actually adding it to the DOM.
        downloadLink.href = window.webkitURL.createObjectURL(textFileAsBlob);
    }
    else
    {
        // Firefox requires the link to be added to the DOM
        // before it can be clicked.
        downloadLink.href = window.URL.createObjectURL(textFileAsBlob);
        downloadLink.onclick = destroyClickedElement;
        downloadLink.style.display = "none";
        document.body.appendChild(downloadLink);
    }

    downloadLink.click();
}

$(document).delegate('#text', 'keydown', function(e) {
  var keyCode = e.keyCode || e.which;

  if (keyCode == 9) {
    e.preventDefault();
    var start = $(this).get(0).selectionStart;
    var end = $(this).get(0).selectionEnd;

    // set textarea value to: text before caret + tab + text after caret
    $(this).val($(this).val().substring(0, start)
                + "\t"
                + $(this).val().substring(end));

    // put caret at right position again
    $(this).get(0).selectionStart =
    $(this).get(0).selectionEnd = start + 1;
  }
});