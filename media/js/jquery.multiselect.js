/**
 * @author lzyy <healdream@gmail.com>
 * @copyright 2007 lzyy
 * @license GPL
 * @version 1.0.0
 */



(function($){
	$.fn.multiSelect = function(options){
	  var options = $.extend({
	    submitCallback: false,
	    numPerRow: 5,
	    title: '请选择',
	    checkCallback: false,
	    content: ''
	},options);

	return this.each(function(){
	    $.fn.multiSelect.createSelectDiv($(this).attr("id"), options);
	});
	}

	//创建div
   $.fn.multiSelect.createSelectDiv = function(select_id, opts){
		//固定select的宽，以免被撑大
		$("#"+select_id).width($("#"+select_id).width());

		var $obj=$("#"+select_id +"_open");

		//取得该select的坐标对象
		var offset = $obj.offset();
		//获取select的title值
		var title = $obj.attr("title")==""?"请选择":$obj.attr("title");
		//如果是IE的话将该div往上移一个像素
		if($.browser.msie){
			offset.top -=1;
		}

		//创建table内容tr和td
		$.fn.multiSelect.createDiv(select_id, opts);

		/*
		//如果div过高，则显示滚动条
		if($("#"+select_id+"_div").height()>opts.height){
			$("#"+select_id+"_div").height(opts.height);
			//IE这个老家伙总是要来点hack才舒服
			if($.browser.msie){
				$("#"+select_id+"_div .select_div_title").width($("#"+select_id+"_div").width()-10);
				$("#"+select_id+"_div .select_div_bottom").width($("#"+select_id+"_div").width()-16);
			}
		}
		 */
		//定义打开函数
		$.fn.multiSelect.opener(select_id,opts);
		//定义确定按钮的点击事件
		$.fn.multiSelect.okClick(select_id,opts);
     		$.fn.multiSelect.cancelCallback(select_id);
		$.fn.multiSelect.checkCallback(select_id);
	}

	$.fn.multiSelect.okClick=function(select_id,opts){
	  var div  = $("#" + select_id + "_div");
	  div.find("input[type='button'][name='submit']").click(function(){

   	    var options = div.find("input[type='checkbox'][name!='all_select']:checked");
	    var op_values = [];
	    options.each(function(){
	      op_values.push($(this).val());
	    });
	    var val = op_values.join(",");
	    var prefix = select_id.split("_")[1];
            if(prefix == "provname")
            {
                $.post("/area/",{province:val},function(text){
		  var city = select_id.replace("provname", "cityname");
		  $("#" + city + "_div").remove();
		  $("#" + city).multiSelect({'content':text});
                });

            }
            else
            {jQuery.post("/query/",{query:val});
            }

	    $("#" + select_id  + "_open").val(val);
            //$("#pi").multiSelect({width:300,height:150,iframe:false});
			$("#"+select_id+"_div").slideUp("fast",function(){
				if(!opts.iframe){
				$("#"+select_id).css("visibility","visible");
			}
			});
		});
	}

	//定义打开div函数
	$.fn.multiSelect.opener = function(select_id,opts){
		$obj = $("#"+select_id+"_open");
        //$obj = $("#pop"+select_id+"_open");
		$obj.unbind('click');//取消绑定，避免反复弹出
		$obj.click(function(){
			//关掉所有打开的div
			$(".select_div").slideUp("fast");
			//$("select").css("visibility","visible");
			$("#"+select_id).css("visibility","hidden");
			$("#"+select_id+"_div").slideDown("fast");
		});
	}
   //hide the div when user clicked cancel button.
   $.fn.multiSelect.cancelCallback = function(select_id) {
     var div = $("#" + select_id + "_div");
     div.find("input[type='button'][name='cancel']").click(function(){
       div.slideUp("fast");
       });

   }

   $.fn.multiSelect.checkCallback = function(select_id){
     var div = $("#" + select_id + "_div");
     var prefix = select_id.split("_")[1];
       div.find("input[type='checkbox']").each(function(){
	 var obj = $(this);
	 obj.click(function(){
	   if (obj.attr("name") == 'all_select'){
	     if (this.checked) {
	       div.find("input[type='checkbox']").attr("checked", true);
	     }
	     else {
	       div.find("input[type='checkbox']").attr("checked", false);
	     }
	   }
	   else {
	     var all_select = div.find("input[name='all_select']");

	     if (!this.checked) {
	       all_select.attr("checked", false);
	     }
	     else {
	       var checkbox_num = div.find("input[type='checkbox'][name!='all_select']").length;
	       var checked_num = div.find("input[type='checkbox'][name!='all_select']:checked").length;
	       if (checkbox_num != checked_num) {
		 return true;
	       }
	       all_select.attr("checked", true);
	     }
	   }
	   });})}



   $.fn.multiSelect.createDiv = function(select_id, opts){
     var div = $('<div class="select_div" id="' + select_id + '_div" style="position:absolute; display:none; padding:0px; left:360px; top:240px; z-index:15; width: 608px;"></div>');
     $(document.body).append(div);
     if (opts['content']) {
       var table = $(opts['content']);
       div.append(table);
       return true;
     }

	  var table = $('<table width="100%" cellspacing="1" cellpadding="3" border="0" bgcolor="#CCCCCC">');
	  div.append(table);

	  var tbody = $("<tbody></tbody>");
	  table.append(tbody);

	  if (opts['title']) {
	    var tr = $('<tr><td height="30" bgcolor="#666666" style="padding-left: 5px;" class="z_da"><span class="z_c">' + opts['title'] + '</span></td></tr>');
	    tbody.append(tr);
	  }

	  var num = opts['numPerRow'];

	  var $child = $("#"+select_id);
	  var childLength = $child.children().length;
	  var content = []
	  for(var i=0;i<childLength;i++){
	    text = $child.children().eq(i).text();
	    val = $child.children().eq(i).val()
	    var op = "";
	    if (i % num == 0) {
	      op = "<tr><td height='25' bgcolor='#FFFFFF'><div><ul class='select_line'>";
	    }
	    op = op + "<li><input type='checkbox' name='checkbox' checked='checked' value='"+ val + "' />" + text + "</li>";
	    if (i % num == num -1) {
	      op += "</ul></div></td></tr>";
	    }
	    content.push(op);
	  }

	  content.push("</td></tr>");
	  content = content.join("");
	  var confirm = '<tr><td height="30" align="left" bgcolor="#FFFFFF"><span style="padding-right:55px; padding-left:110px;"><input type="checkbox" checked="checked" name="all_select" />全选</span><input type="button" name="submit" value=" 确 定 "/>&nbsp;<input type="button" name="cancel" value=" 取 消 "/></td></tr>'

	  tbody.append(content);
	  tbody.append(confirm);

	  return true;
	}
})(jQuery);


