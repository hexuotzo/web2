FIELD_CNAME_MAPPING = {'name': '字段名:', 'cname': '中文名:'}
FIELDSET = "<fieldset class='module aligned dynamic'></fieldset>";

$("document").ready(function(){
    load_json();
    
    // stringify json for submitting.
    $("div.submit-row").find("input[type=submit]").click(function(){
        var json = build_json();
        var body = $("<input name='body' type='hidden'></input>");
        $("form#view_form").append(body);
        body.attr("value", JSON.stringify(json));
    });
    
    $("input.add").click(function(){
        /* 
        append a new row for editing.
        jquery clone method has bug in ie, so I have to do that manually.
        */
        var rows = $(this).parent().find("div.form-row");
        var length = rows.length;
        var row = rows.eq(length - 1);
        var name = row.find("input[type=text]").eq(0).attr("name");
        var index = Number(name.split("_")[1]) + 1;
        var new_row = $("<div class='form-row'></div>");
        new_row.insertAfter(row);
        var block = build_block('name', {}, index);
        new_row.append(block);
        var block = build_block('cname', {}, index);
        new_row.append(block);
    });
});

function load_json() {
/*
    parse json and generate new layout to replace existing textarea.
*/  
    var body = $("div.body");
    var json = body.find("#id_body").text();

    fieldset = body.parent();
    body.remove();

    if (json) {
        json = JSON.parse(json);
        }
    else {
        json = {'query': {'cname': '条件', 'values': []},
            'dimension': {'cname': '维度', 'values': []},
            'indicator': {'cname': '指标', 'values': []}
            };
    }

    for (var key1 in json) {
        var values = json[key1]['values'];
        var new_fieldset = $(FIELDSET);
        new_fieldset.insertAfter(fieldset);
        new_fieldset.attr("id", key1);
        var cname = json[key1]['cname'];
        if (cname) {
            new_fieldset.append("<h2>" + cname + "</h2>");
        }
        new_fieldset.append("<input type='button' class='add' value='添加'></input>")

        for (var index in values) {
            var container = $("<div class='form-row'></div>");
            new_fieldset.append(container);
        
            for (var key2 in values[index]) {
                container.append(build_block(key2, values[index][key2], index));
            }
        }
        if (values.length == 0) {
            // if values is empty, initialize with 2 fields.
            var container = $("<div class='form-row'></div>");
            new_fieldset.append(container);            
            container.append(build_block('name', {}, 0));
            container.append(build_block('cname', {}, 0));
        }
    }
}

function build_block(key2, data, index) {
    var block = $("<div class='field-box'></div>");
    field_name = FIELD_CNAME_MAPPING[key2];
    var label = $("<label>" + field_name +"</label>");
    block.append(label);
    var input = $("<input type='text' max_length=50></input>");
    block.append(input);
    var value = data? data['value'] : '';
    input.attr("value", value);
    input.attr("name", key2 + "_" + index);
    return block;
}

function build_json() {
/*
    collect fields input and convert them to a json object.
*/
    var json = {}
    var fieldsets = $("fieldset.dynamic");
    fieldsets.each(function(){
        var id = $(this).attr("id");
        json[id] = {'values': []};
        json[id]['cname'] = $(this).find("h2").text();
        
        $(this).find("div.form-row").each(function(){
            // uncomplete make record of uncomplete field
            var uncomplete = false;
            var push = false;
            $(this).find("input").each(function(){
            var name = $(this).attr("name");
            var key = name.split("_")[0];
            var index = name.split("_")[1];
            if (uncomplete) {
                // if the field is not filled, continue to next loop
                return true;
            }
            
            var value = $(this).attr("value");
            if (!value) {
                if (push) {
                    json[id]['values'].pop();
                }
                uncomplete = true;
            }
            else {
                    if (push) {
                        var len = json[id]['values'].length;
                        json[id]['values'][len-1][key] = {'value': value};
                    }
                    else {
                        var d= {};
                        d[key] = {'value': value};
                        json[id]['values'].push(d);
                    }
                    push = true;
            }
        })
        })
    });
    return json;
}

function indexOf(el, arr) {
/* 
    thanks to stupid IE, I have to write my own function to check whether 
an element is in a array. just use it as a utility, don't want to 
pollute prototype. Remind me if you have a better solution.
*/
    for (var i in arr) {
        if (el == arr[index]) {
            return i;
        }
    }
    return -1;
}