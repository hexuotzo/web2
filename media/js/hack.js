$(document).ready(function(){
	$("div.body").remove();
	var url = '/get_view_option/';
	$("#id_dataset").change(function(){
		var val = $(this).val();
		var view_id = $("input[name='view_id']").val() || "";
		$.post(url, {"dataset": val, 'view_id': view_id}, show_option, "html");
	});

	// stringify json for submitting.
	$("div.submit-row").find("input[type=submit]").click(function(){
	var json = build_json();
        var body = $("<input name='body' type='hidden'></input>");
        $("form#view_form").append(body);
	body.attr("value", JSON.stringify(json));
	$("fieldset.dynamic").remove();
    });
});

function show_option(html, status) {
  $("fieldset.dynamic").remove();
  $("div.submit-row").before(html);

}

function build_json(){
/*
    collect fields input and convert them to a json object.
*/
  var json = [];
  var fieldsets = $("fieldset.dynamic");
  fieldsets.each(function(){
		   data = {};
		   var id = $(this).attr("id");
		   data[id] = {'values': []};
		   data[id]['cname'] = $(this).find("h2").text();
		   $(this).find("input[name='check']:checked").each(function(){
								      var value = {};
								      var fields = $(this).parent().nextAll().find("select,input");
								      fields.each(function(){
										    var obj = $(this);
										    var name = obj.attr("name");
										    var obj_value = {};
										    var cname = $(this).prev("label").text();

										     obj_value['cname'] = cname.substring(0, cname.length - 1);
										     if (obj.attr("type").toLowerCase() == 'checkbox'){
										      obj_value['value'] = obj.attr("checked");
										    }
										    else {
											obj_value['value'] = obj.val();
										      }
										    value[name] = obj_value;
										  });

								      if (value['name']['value'] == 'date'){
									value['name']['value'] = 'begin_date';
									value['cname']['value'] = '起始时间';
									data[id]['values'].push(value);
									var end_date = jQuery.extend(true, {}, value);
									end_date['name']['value'] = 'end_date';
									end_date['cname']['value'] = '终止时间';
									data[id]['values'].push(end_date);

								      }
								      else {
									data[id]['values'].push(value);
								      }
								    });
		   json.push(data);
		 });
  return json;
}
