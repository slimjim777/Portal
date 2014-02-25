
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
