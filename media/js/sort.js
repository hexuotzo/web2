//Author    :  狼Robot
//Contact  :  robot@k2046.cn
//Date      :  2008-04-19
//Explain  :  使Table可以点击排序.
/*使用说明  :
方法1:
new TableSorter("tb1");
效果:
id为tb1的table的第一行任意单元格都可以点击进行排序.
方法2:
new TableSorter("tb1", 0, 1, 3);
效果:
id为tb1的table的第一行0,1,3单元格可以进行点击排序.
*/
function TableSorter(table)
{
this.Table = this.$(table);
if(this.Table.rows.length <= 1)
{
return;
}
this.Init(arguments);
}
//以下样式针对表头的单元格.
TableSorter.prototype.NormalCss = "d1";//没有执行排序时的样式.
TableSorter.prototype.SortAscCss = "d2";//升序排序时的样式.
TableSorter.prototype.SortDescCss = "d3";//降序排序时的样式.
//初始化table的信息和操作.
TableSorter.prototype.Init = function(args)
{
this.ViewState = [];
for(var x = 0; x < this.Table.rows[0].cells.length; x++)
{
this.ViewState[x] = false;
}
if(args.length > 1)
{
for(var x = 1; x < args.length; x++)
{
if(args[x] > this.Table.rows.length)
{
continue;
}
else
{
this.Table.rows[0].cells[args[x]].onclick = this.GetFunction(this,"Sort",args[x]);
this.Table.rows[0].cells[args[x]].style.cursor = "pointer";
}
}
}
else
{
for(var x = 0; x < this.Table.rows[0].cells.length; x++)
{
this.Table.rows[0].cells[x].onclick = this.GetFunction(this,"Sort",x);
this.Table.rows[0].cells[x].style.cursor = "pointer";
}
}
}
//简写document.getElementById方法.
TableSorter.prototype.$ = function(element)
{
return document.getElementById(element);
}
//取得指定对象的脱壳函数.
TableSorter.prototype.GetFunction = function(variable,method,param)
{
return function()
{
variable[method](param);
}
}
//执行排序.
TableSorter.prototype.Sort = function(col)
{
var SortAsNumber = true;
for(var x = 0; x < this.Table.rows[0].cells.length; x++)
{
this.Table.rows[0].cells[x].className = this.NormalCss;

}
var Sorter = [];
for(var x = 1; x < this.Table.rows.length-1; x++)
{
Sorter[x-1] = [this.Table.rows[x].cells[col].innerHTML, x];
SortAsNumber = SortAsNumber && this.IsNumeric(Sorter[x-1][0].replace(/[%.]/,'').replace(/[^0-9.-]/g,''));
}
if(SortAsNumber)
{
for(var x = 0; x < Sorter.length; x++)
{
for(var y = x + 1; y < Sorter.length; y++)
{
if(parseFloat(Sorter[y][0].replace(/[%.]/,'').replace(/[^0-9.-]/g,'')) < parseFloat(Sorter[x][0].replace(/[%.]/,'').replace(/[^0-9.-]/g,'')))
{
var tmp = Sorter[x];
Sorter[x] = Sorter[y];
Sorter[y] = tmp;
}
}
}
}
else
{
Sorter.sort();
}
if(this.ViewState[col])
{
Sorter.reverse();
this.ViewState[col] = false;
this.Table.rows[0].cells[col].className = this.SortDescCss;
}
else
{
this.ViewState[col] = true;
this.Table.rows[0].cells[col].className = this.SortAscCss;
}
var Rank = [];
for(var x = 0; x < Sorter.length; x++)
{
Rank[x] = this.GetRowHtml(this.Table.rows[Sorter[x][1]]);
}
for(var x = 1; x < this.Table.rows.length; x++)
{
for(var y = 0; y < this.Table.rows[x].cells.length; y++)
{
this.Table.rows[x].cells[y].innerHTML = Rank[x-1][y];
}
}
this.OnSorted(this.Table.rows[0].cells[col], this.ViewState[col]);
}
//取得指定行的内容.
TableSorter.prototype.GetRowHtml = function(row)
{
var result = [];
for(var x = 0; x < row.cells.length; x++)
{
result[x] = row.cells[x].innerHTML;
}
return result;
}
TableSorter.prototype.IsNumeric = function(num)
{
return /^\d+[\.\d+]?$/.test(num);
}
//可自行实现排序后的动作.
TableSorter.prototype.OnSorted = function(cell, IsAsc)
{
return;
}
