mui.init();
mui.ready(function() {

    let userPicker = new mui.PopPicker();
    let currentSelectedIndex = 0;
    let currentStatus = 'Play';
    let currentPosition = 0;
    let videoDuration = 0;
    let device_key = '{device_key}';
    let api_url = '../api/' + device_key;
    let isSeeking = false;

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

    var lightVideo = document.getElementById('light');
    var lightHandle = document.getElementById('light-handle');

	/*lightVideo.addEventListener('ended', function(){
		if (lightVideo.classList.contains('mui-switch')) {
			lightVideo.play();
		} else {
			lightVideo.stop();
		}
	});*/


    //屏幕常亮
	lightHandle.addEventListener('toggle', function(event) {
	    if (event.detail.isActive) {
	        lightVideo.play();
	    } else {
	        lightVideo.pause();
	    }
	});

    function light(){
        lightVideo.play();
        document.getElementById('light-handle').classList.remove('mui-active')
    }

    function nolight() {
        lightVideo.stop();
        document.getElementById('light-handle').classList.add('mui-active')
    }


    //进度跳转
    let offset = 0
    function updateSeekInfo(t) {
        formattedTime = formatTime(t);
        if (!formattedTime.startsWith('-') && t != 0) {
            formattedTime = '+' + formattedTime;
        }
        document.getElementById('timeOffsetInfo').innerHTML =
          (t == 0 ? '' : formattedTime + '/')
        +formatTime(currentPosition)
        + (t == 0 ? '' : '(' + formatTime(currentPosition + t)  + ')');
    }
    updateSeekInfo(0);
    let seekBtnFunc = function() {
        isSeeking = true
        offset += parseInt(this.getAttribute('timeOffset'));
        if ((offset < 0) && (currentPosition + offset < 0) ) {
            offset = -currentPosition;
        } else if (offset + currentPosition > videoDuration) {
            offset = videoDuration - currentPosition;
        }
		updateSeekInfo(offset);
	};
	let seekBtnEndFunc = debounce(function() {

	    mui.getJSON(api_url,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        isSeeking = false;
	    }, 1000)
	}, 1000);

	let offsetBtns = document.querySelectorAll('.timeSeekButton')
	for (let ob of offsetBtns) {
		ob.addEventListener('click', seekBtnFunc)
		ob.addEventListener('click', seekBtnEndFunc)
	}

    let startPos = 0
    let progressBar = document.getElementById('progressBar');
    let rangeSeekStartFunc = function(){
        startPos = currentPosition;
        isSeeking = true
    }

	let rangeSeekFunc = function() {
	    offset = progressBar.value - startPos
	    updateSeekInfo(offset);
	};
	let rangeSeekEndFunc =function() {

	    mui.getJSON(api_url,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    startPos = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        isSeeking = false;

	    }, 1000)

	};


	progressBar.min = 0;
	progressBar.max = videoDuration;
	progressBar.addEventListener('mousedown', rangeSeekStartFunc);
	progressBar.addEventListener('touchstart', rangeSeekStartFunc);
	progressBar.addEventListener('input', rangeSeekFunc);
	progressBar.addEventListener('mouseup', rangeSeekEndFunc);
	progressBar.addEventListener('touchend', rangeSeekEndFunc);

    //数据更新
    function updateData() {
        if (!isSeeking) {
            mui.getJSON(api_url,{command:'status', r: '' +new Date().getTime()},function(data){

                    if (!isSeeking) {
                        console.log(data);
                        document.getElementById('current_file_name').innerHTML = data.file_name;
                        document.getElementById('current_file_time').innerHTML = data.position + '/' + data.duration;
                        document.getElementById('select-video').innerHTML = data.file_name;

                        currentPosition = data.position;
                        videoDuration = data.duration;
                        currentStatus = data.current_status;

                        currentSelectedIndex = data.index;
                        mui('#video-progress-bar').progressbar().setProgress(Math.round(data.position/data.duration*100));
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

                        progressBar.max = videoDuration;
                        progressBar.value = currentPosition;

                        timeInfoText = formatTime(currentPosition) + '/' + formatTime(videoDuration)
                        document.getElementById('timeInfo').innerText = timeInfoText
                        updateSeekInfo(0)
                    }

                }
            );
        }

    }

    updateData();

    setInterval(updateData, 500)
});