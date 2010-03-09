function init_dimension(user_id, url){
	$("span.sp").find("input[type=checkbox]").click(function(){
	var boxes = $(this).parents("div.dimension").find("input[type=checkbox]");
	var d = [];
	boxes.each(function(){
	if ($(this).attr("checked")) {
	d.push($(this).attr("name"));
	}
	});

	var select_di = $(this).parents("div.dimension").next("div.dimension_popup").find("select[name='checked']");
	if ($(this).attr("checked")) {
	var op = $("<option value='" + $(this).attr("name") + "'>" + jQuery.trim($(this).parent().text()) +"</option>")
	select_di.append(op);
	}
	else {
	var ops = select_di.find("option");
	var val = $(this).attr("name");
	ops.each(function(){
	if ($(this).val() == val){
	$(this).remove();
	return true;
	}
	});
	}

	d = d.join(",");
	var view_id = $(this).parents("div.dimension").nextAll("div.container").find("input[name='view_id']").val();
	jQuery.post(url, {"dimension": d, "user_id": user_id, "view_id": view_id});
	});

$(".more_dimension").click(function(){
var popup = $(this).parents("div.dimension").next("div.dimension_popup");
if (!popup.length) {
return false;
}
popup.show();
});

$(".dimension_popup").find("input[type='button'][name='add']").click(function(){
var opts = $(this).parent("td").prev("td").find("select.all option:selected");
var checked = $(this).parent("td").next("td").find("select[name='checked']");
opts.each(function(){
var op = $(this);
var already_checked = false;
checked.find("option").each(function(){
if ($(this).val() == op.val()) {
	already_checked = true;
	return false;
}
});
if (!already_checked) {
	checked.append(op.clone());
}
})});

$(".dimension_popup").find("input[name='remove']").click(function(){
var checked = $(this).parent("td").next("td").find("select[name='checked']");
checked.find("option:selected").remove();
});

$(".dimension_popup").find("input[name='cancel']").click(function(){$(this).parents(".dimension_popup").hide();});

$(".dimension_popup").find("input[name='submit']").click(function(){
var opts = $(this).parents(".dimension_popup").find("select[name='checked'] option");
var selected_val = [];
opts.each(function(){
	selected_val.push($(this).val());
});
var main_di = $(this).parents(".dimension_popup").prev(".dimension").find("input[type='checkbox']");

main_di.each(function(){
if (selected_val.indexOf($(this).attr("name")) != -1) {
$(this).attr("checked", true);
}
else {
$(this).attr("checked", false);
}
});

dimensions = selected_val.join(",");
var view_id = $(this).parents("div.dimension_popup").nextAll("div.container").find("input[name='view_id']").val();
jQuery.post(url, {"dimension": dimensions, "user_id": user_id, "view_id": view_id});
$(this).parents(".dimension_popup").hide();
});
}

function init_calendar(){
        //initialize calendar
        var today = new Date();
        var today = today.valueOf();
        today = today-24*60*60*1000;
        var today = new Date(today);
        var month = today.getMonth()+1;
        if(12 > month){
        month = "0"+month;
        }
	// get all time select inputs and bind events.
	var widgets = $("input.time_query");
	widgets.each(function(){
	var obj = $(this);
	Calendar.setup({inputField:obj.attr("id"),ifFormat:"%Y-%m-%d",singleClick:true,timeFormat:"24",step:1});
	});
}

function init_multiselect(content){
	var multi_query = $(".multi_query").nextAll("div").find("select");
	$(".multi_query").each(function(){
	var name = $(this).prev("label").text();
	name = name.split(":")[0];
	var title = "请选择" + name;
	var id = $(this).attr("id");
	var params = {"title": title};
	if (id.match(/[a-z]+_cityname/)) {
	params["content"] = content;
	}
	$(this).nextAll("div").find("select").multiSelect(params);
	});
}
