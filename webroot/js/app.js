mui.init()
mui.ready(function() {

    let userPicker = new mui.PopPicker();
    let currentSelectedIndex = 0;
    let currentStatus = 'Play'
    let currentPosition = 0
    let device_key = '{device_key}'
    let api_url = '../api/' + device_key

    circleProgress = new CircleProgress('.circle-progress-content')
        .attr('max', 100)
        .attr('value', 0)
        .attr('animationDuration', 0)
        .attr('textFormat', function(value, max) {
            if(currentStatus == 'Play') {
                return '&#xf04b'
			} else {
				return "&#xf04c";
			}
		});

	mui('#circle-progress-wrapper').on('click', '.circle-progress-content', function(){
	    cmd = ''
		if(currentStatus == 'Play') {
			currentStatus = 'Pause'
			cmd = 'pause'
		} else {
		    currentStatus = 'Play'
		    cmd = 'play'
		}
		//circleProgress.attr({ value: currentPosition, });

        mui.getJSON(api_url,{command:cmd, r: '' +new Date().getTime()},function(data){
            }
        );

	})



    function updateData() {
        mui.getJSON(api_url,{command:'status', r: '' +new Date().getTime()},function(data){
                console.log(data);
                document.getElementById('current_file_name').innerHTML = data.file_name;
                document.getElementById('current_file_time').innerHTML = data.position + '/' + data.duration;
                document.getElementById('select-video').innerHTML = data.file_name;

                currentPosition = data.position
                currentStatus = data.current_status

                currentSelectedIndex = data.index;
                mui('#video-progress-bar').progressbar().setProgress(Math.round(data.position/data.duration*100))
                let pickerData = new Array();
                for(let i = 0; i < data.file_name_list.length; i++) {
                    pickerData[i] = {
                        value: i + '',
                        text: data.file_name_list[i]
                    };
                }
                userPicker.setData(pickerData);
                circleProgress.attr({ max: data.duration, });
                circleProgress.attr({ value: data.position, });
            }
        );
    }

    updateData();

    setInterval(updateData, 500)


/*
	mui('#video-progress-bar').progressbar().setProgress(50)

	mui(".flex-container").on('click', '#btn-play', function(){
		if(this.querySelector("span").classList.contains('fa-play')){
			this.querySelector("span").classList.remove('fa-play')
			this.querySelector("span").classList.add('fa-pause')
			this.classList.remove('play')
			this.classList.add('pause')
		} else {
			this.querySelector("span").classList.add('fa-play')
			this.querySelector("span").classList.remove('fa-pause')
			this.classList.remove('pause')
			this.classList.add('play')
		}
	})
	*/
	var showUserPickerButton = document.getElementById('select-video');
	showUserPickerButton.addEventListener('tap', function(event) {
		userPicker.pickers[0].setSelectedIndex(currentSelectedIndex, 1000)
		userPicker.show(function(items) {
		    userSelectIndex = parseInt(items[0].value)
            mui.getJSON(api_url,{command:'index', index: userSelectIndex, r: '' +new Date().getTime()},function(data){
                    console.log(data);
                    showUserPickerButton.innerText = items[0].text;
                }
            );

			//返回 false 可以阻止选择框的关闭
			//return false;
		});
	}, false);
})