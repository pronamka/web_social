
class ChartBuilder{
    constructor(){
        this.current_chart = null
        this.loaded = {'on_post_activity': false, 'over_time_activity': false}
        this.loaded_all = {'on_post_activity': false, 'over_time_activity': false}
        this.charts_info = {'on_post_activity': {'views': [], 'likes': [], 'comments': []}, 
                    'over_time_activity': {'views': [], 'likes': [], 'comments': []}}
        
        this.charts_loading_parameters = {'on_post_activity': 0, 'over_time_activity': 0}

        this.charts_properties = {'views': 0, 'likes': 1, 'comments': 2}

        this.charts_changing_order = {'on_post_activity': 'over_time_activity', 
                                      'over_time_activity': 'on_post_activity'}

        this.charts_titles = {'on_post_activity': 'Activity under your posts', 
                              'over_time_activity': 'Activity over time'}
    }

    preCheckChartLoadingConditions(chart_name){
        if (this.loaded_all[chart_name] == false){
            document.getElementById('load-more-charts-button').disabled = false
        }
    }

    sendChartInfoRequest(chart_name, amount){
        return sendRequest('POST', '/load_info/', {
            'page': 'analytics', 
            'chart': chart_name, 
            'required': amount, 
            'loaded':  this.charts_loading_parameters[chart_name]}).then(resp=>{
                this.charts_loading_parameters[chart_name] += amount
                return JSON.parse(resp)['analytics']
            })
    }

    checkIfEmpty(chart_name, response){
        if (response['views'].length == 0){
            alert('No more info found')
            document.getElementById('load-more-charts-button').disabled = true
            this.loaded_all[chart_name] = true
            return true;
        }
        return false;
    }

    fillChartsInfo(chart_name, response){
        for(var i in this.charts_properties){
            this.charts_info[chart_name][i] = response[i].concat(
                this.charts_info[chart_name][i])
        }
    }

    loadChartInfo(chart_name){
        if (chart_name == null){
            chart_name = this.current_chart
        }
        
        this.preCheckChartLoadingConditions(chart_name)
        this.sendChartInfoRequest(chart_name, 30).then(resp=>{
            this.checkIfEmpty(chart_name, resp)
            this.fillChartsInfo(chart_name, resp)
            this.displayChart(chart_name)
        })
        this.current_chart = chart_name
        this.loaded[chart_name] = true
    }


    checkLoadMoreInfoButtonState(chart_name){
        if (this.loaded_all[chart_name] == false){
            document.getElementById('load-more-charts-button').disabled = false
        }
        else{
            document.getElementById('load-more-charts-button').disabled = true
        }
    }


    displayChart(chart_name){
        this.checkLoadMoreInfoButtonState(chart_name)

        JSC.Chart('analytics-chart', {
            title_label_text: this.charts_titles[chart_name],
            axisToZoom: 'xy', 
            yAxis_scale_zoomLimit: 1000, 
            xAxis: { 
                formatString: 'n1', 
                scale_zoomLimit: 1 
            }, 
            annotations: [ 
                { 
                  position: 'inside top', 
                  margin: 5, 
                  label_text: 
                    'Click-Drag the chart area to zoom.'
                } 
              ], 
            series: [
                {name: "veiws", points: this.charts_info[chart_name]['views']}, 
                {name: "likes", points: this.charts_info[chart_name]['likes']},
                {name: 'comments', points: this.charts_info[chart_name]['comments']}
            ], 
        })
        this.current_chart = chart_name
    }

    changeChart(){
        const chart_to_load = this.charts_changing_order[this.current_chart]
        if(!this.loaded[chart_to_load]){
            this.loadChartInfo(chart_to_load)
        }
        else{
            this.displayChart(chart_to_load)
        }
    }
}

function loadFirstChart(){
    chart_builder.loadChartInfo('on_post_activity')
}

const chart_builder = new ChartBuilder()


$('#load-more-charts-button').on('click',() => {chart_builder.loadChartInfo(null)})

$('#change-chart-button').on('click', () => {chart_builder.changeChart()})

