
function adminTogglePartner(el, nextState, personId) {
    var postdata = {
        personid: personId,
        action: nextState,
        type: 'partner'
    };
    
    var classNameUndo;
    
    if (nextState == 'rw') {
        // Enable manage rights to partner
        classNameUndo = '';
        $(el).attr('class', 'ui-corner-all ui-state-active');
    } else if (nextState == 'ro') {
        // Enable view rights to partner
        classNameUndo = 'ui-corner-all ui-state-active';
        $(el).attr('class', 'ui-corner-all ui-state-default');
    } else {
        // Disable rights to partner
        classNameUndo = 'ui-corner-all ui-state-default';
        $(el).attr('class', '');
    }
    
    $( "#progressbar" ).show();
    
    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/user_access',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $(el).attr('class', classNameUndo);
        } else {
            document.location.href = '/accounts/' + personId;
            $( "#progressbar" ).hide();
        }
      }
    });
}


function adminToggleKeyLeader(el, nextState, personId) {
    var postdata = {
        personid: personId,
        action: nextState,
        type: 'key_leader'
    };
    
    var classNameUndo;
    
    if (nextState == 'rw') {
        // Enable manage rights to key-leader
        classNameUndo = '';
        $(el).attr('class', 'ui-corner-all ui-state-active');
    } else if (nextState == 'ro') {
        // Enable view rights to team-serving
        classNameUndo = 'ui-corner-all ui-state-active';
        $(el).attr('class', 'ui-corner-all ui-state-default');
    } else {
        // Disable rights to team-serving
        classNameUndo = 'ui-corner-all ui-state-default';
        $(el).attr('class', '');
    }
    
    $( "#progressbar" ).show();
    
    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/user_access',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $(el).attr('class', classNameUndo);
        } else {
            document.location.href = '/accounts/' + personId;
            $( "#progressbar" ).hide();
        }
      }
    });
}


function contactToggleFilter(el) {
    var fieldName = $(el).text();
    var className = 'ui-corner-all ui-state-active';
    
    // Clear the fields array
    fields.length = 0;

    // Mark the button as selected/unselected    
    if (!$(el).attr('class')) {
        $(el).attr('class', className);
    } else {
        $(el).attr('class', '');
    }
    
    // Populate the fields array
    if ($('#partner').attr('class')) {
        fields.push( 'partner' );
    }
    if ($('#keyleader').attr('class')) {
        fields.push( 'key_leader' );
    }
    
    // Search for the list of people in those groups
    var postdata = {
        groups: groups,
        fields: fields
    };

    var p = $('#c-people');
    p.empty();
    $( "#progressbar" ).show();
    
    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/person/groups',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
          var emails = [];
          var table = '<table class="grid"><tr><th>Name</th><th>Email</th><th>Home Phone</th><th>Mobile Phone</th></tr>';
          for (dd in data.result) {
              var d = data.result[dd];
              table += '<tr><td><a id="c-' + d.personid +'" href="/people/'+ d.personid +'">' + d.name + '</a></td>' +
                      '<td>' + d.email + '</td><td>' + d.home_phone + '</td><td>' + d.mobile_phone + '</td></tr>';
              if (d.email) {
                emails.push( d.name + ' \<' + d.email + '\>' );
              }
          }
          table += '</table>';
          p.append(table);
          $('#c-email').text(emails.join(', '));
        
          $('#accordion').accordion('refresh');
          $( "#progressbar" ).hide();
      }
    });
}


function contactToggleServing(el) {
    var groupName = $(el).text();
    var className = 'ui-corner-all ui-state-active';
    
    if (!$(el).attr('class')) {
        $(el).attr('class', className);
        groups.push( groupName );
    } else {
        $(el).attr('class', '');
        
        groups = $.grep(groups, function(value) {
            return value != groupName;
        });
    }
    
    // Search for the list of people in those groups
    var postdata = {
        groups: groups,
        fields: fields
    };

    var p = $('#c-people');
    p.empty();
    $( "#progressbar" ).show();
    
    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/person/groups',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
          var emails = [];
          var table = '<table class="grid"><tr><th>Name</th><th>Email</th><th>Home Phone</th><th>Mobile Phone</th></tr>';
          for (dd in data.result) {
              var d = data.result[dd];

              table += '<td><a id="c-' + d.personid +'" href="/people/'+ d.personid +'">' + d.name + '</a></td>' +
                      '<td>' + d.email + '</td><td>' + d.home_phone + '</td><td>' + d.mobile_phone + '</td></tr>';
              if (d.email) {
                emails.push( d.name + ' \<' + d.email + '\>' );
              }
          }
          table += '</table>';
          console.log(table);
          p.append(table);
          $('#c-email').text(emails.join(', '));
        
          $('#accordion').accordion('refresh');
          $( "#progressbar" ).hide();
      }
    });
}


function personToggleProfile(personid, externalid, field, state) {
    // Search for the list of people in those groups
    var postdata = {
        personid: personid,
        externalid: externalid
    };
    postdata[field] = state;
    
    $( "#progressbar" ).show();
    
    // Update the person record and reload record
    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/person/' + personid,
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            console.log(data);
            $message.text(data.message);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $( "#progressbar" ).hide();
        } else {
            document.location.href = '/people/' + personid;
            $( "#progressbar" ).hide();
        }
      }
    });
}

function registrationFindPerson(name) {

    var postdata = {
        name: name
    };
    
    $( "#progressbar" ).show();
    var p = $('#a-people');
    p.empty();

    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/person/find',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $(el).attr('class', classNameUndo);
        } else {
            var table = '<table class="grid"><tr><th></th><th>Name</th><th>Contact Type</th><th>Gender</th><th>School Year</th></tr>';
            for (dd in data.result) {
                var d = data.result[dd];
                table += "<tr><td><button class=\"a-add\" onclick=\"registrationAdd('" + d.Id + "')\">Add</button></td>";
                table += '<td><a id="c-' + d.ExternalId__c +'" href="/people/'+ d.ExternalId__c +'">' + d.Name + '</a></td>' +
                        '<td>' + d.Contact_Type__c + '</td><td>' + empty(d.Gender__c) + '</td><td>' + empty(d.School_Year__c) + '</td></tr>';
            }
            table += '</table>';
            p.append(table);
            $( ".a-add" ).button({icons: {primary: 'ui-icon-plus'}, text: false});

            $( "#progressbar" ).hide();
        }
      }
    });
}

function empty(field) {
    if (!field) {
        return ''
    } else {
        return field;
    }
}

function registrationRegistered(event_id) {
    var postdata = {
        event_id: event_id
    };

    var p = $('#a-people-attendees');
    p.empty();

    // Add progress bar
    var $progress = $("<div>", {id: "a-progress"});
    $progress.progressbar({value: false});
    p.append($progress)

    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/registrations',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $(el).attr('class', classNameUndo);
        } else {
            var table = '<table class="grid"><tr><th>Name</th><th>Status</th><th></th></tr>';
            for (dd in data.result) {
                var d = data.result[dd];
                table += '<tr><td>' + d.Contact__r.Name + '</td><td>' + d.Status__c + '</td><td><button onclick="registrationDelete(\'' + d.Id + '\')" class="a-remove">Remove</button></td></tr>';
            }
            table += '</table>';
            p.append(table);
            $( ".a-remove" ).button({icons: {primary: 'ui-icon-close'}, text: false});
            $($progress).remove();
        }
      }
    });

}

function registrationDelete(regId) {

    var postdata = {
        reg_id: regId
    };

    var request = $.ajax({
      type: 'DELETE',
      url: '/rest/v1.0/registrations/' + regId,
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        if(data.response=='Failed') {
            var $message = $('#messages');
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
            $(el).attr('class', classNameUndo);
        } else {
            console.log(data);
        }
      }
    });

}

function registrationAdd(contactId) {
    var eventId = $("#event_id").val();
    var postdata = {
        event_id: eventId,
        people: [contactId]
    };

    var request = $.ajax({
      type: 'POST',
      url: '/rest/v1.0/registrations/add',
      data: JSON.stringify(postdata),
      contentType:"application/json",
      dataType: "json",
      success: function(data) {
        var $message = $('#messages');
        if(data.response=='Failed') {
            $message.text(data.error);
            $message.attr('class', 'ui-state-error ui-corner-all');
            $message.show().fadeOut(2000);
        } else {
            console.log(data);
            registrationRegistered(eventId);
            $message.text('Registration successful.');
            $message.show().fadeOut(2000);            
        }
      }
    });

}

