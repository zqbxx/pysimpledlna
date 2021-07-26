mui.init();
mui.ready(function() {

    //let userPicker = new mui.PopPicker();
    let currentSelectedIndex = 0;
    let currentStatus = 'Play';
    let currentPosition = 0;
    let playingFileName = '';
    let videoDuration = 0;
    let device_key = '{device_key}';
    let api_url = '../api/' + device_key;
    let isSeeking = false;

    let playListPicker = new mui.PopPicker();
    let currentSelectedPlaylistIndex = 0;
    let currentPlaylistName = '';

    let mask = mui.createMask();

    // 圆形进度条
    circleProgress = new CircleProgress('.circle-progress-content')
        .attr('max', 100)
        .attr('value', 0)
        .attr('animationDuration', 0)
        .attr('textFormat', function(value, max) {
            if(currentStatus == 'Play') {
                return '&#xf04c';
			} else if (currentStatus == 'Pause' || currentStatus == 'Stop') {
				return '&#xf04b';
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

    // 视频选择
	/*var showUserPickerButton = document.getElementById('select-video');
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
	}, false);*/

    //屏幕常亮
    var lightVideo = document.getElementById('light');
    var lightHandle = document.getElementById('light-handle');
    var noSleep = new NoSleep();

	lightHandle.addEventListener('toggle', function(event) {
	    if (event.detail.isActive) {
	        noSleep.enable()
	    } else {
	        noSleep.disable();
	    }
	});


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

                        playlist_changed = currentPlaylistName != data.current_playlist_name;
                        current_video_changed = currentSelectedIndex != data.index;
                        video_position_changed = currentPosition !=  data.position;
                        player_status_changed = currentStatus != data.current_status

                        //document.getElementById('select-video').innerHTML = data.file_name;
                        //播放器状态
                        currentPosition = data.position;
                        videoDuration = data.duration;
                        currentStatus = data.current_status;
                        playingFileName = data.playing_file_name
                        playingFilePath = data.playing_file_path
                        //播放列表状态
                        currentPlaylistName = data.current_playlist_name;
                        currentSelectedIndex = data.index_in_playlist;


                        document.getElementById('current_file_name').innerHTML = data.file_name;
                        document.getElementById('current_file_time').innerHTML = data.position + '/' + data.duration;

                        mui('#video-progress-bar').progressbar().setProgress(Math.round(data.position/data.duration*100));
                        circleProgress.attr({ value: data.position, });

                        if (playlist_changed) {
                            /*let pickerData = new Array();
                            for(let i = 0; i < data.file_name_list.length; i++) {
                                pickerData[i] = {
                                    value: i + '',
                                    text: data.file_name_list[i]
                                };
                            }
                            userPicker.setData(pickerData);*/

                            document.getElementById('playlist-name').innerText = currentPlaylistName;
                            createPlaylistVideos(data.file_name_list, data.index);
                        }

                        if (current_video_changed){
                            circleProgress.attr({ max: data.duration, });
                            progressBar.max = videoDuration;
                        }

                        if (video_position_changed) {
                            progressBar.value = currentPosition;
                            timeInfoText = formatTime(currentPosition) + '/' + formatTime(videoDuration);
                            document.getElementById('timeInfo').innerText = timeInfoText;
                            updateSeekInfo(0);
                        }

                        if (current_video_changed || playlist_changed) {
                            updatePlaylistVideoStatus(data)
                        }

                    }

                }
            );
        }

    }

    //获取播放列表
    function getAllPlaylist() {
        mui.getJSON(api_url,{command:'getAllPlaylist', r: '' +new Date().getTime()}, function(data){
            console.log(data);
            let pickerData = new Array();
            for(let i = 0; i < data.length; i++) {
                pickerData[i] = {
                    value: data[i],
                    text: data[i]
                }
            }
            playListPicker.setData(pickerData)
        });
    }

    mui('#morePlaylist')[0].addEventListener('tap', function(){
		//userPicker.pickers[0].setSelectedIndex(currentSelectedIndex, 1000)
		playListPicker.pickers[0].setSelectedValue(currentPlaylistName, 1000)
		playListPicker.show(function(items) {
		    selectedPlaylistName = items[0].value
		    if (selectedPlaylistName == currentPlaylistName) {
		        return
		    }
		    mask.show();
		    mui.getJSON(api_url,{command:'switchPlayList', o: '', n: selectedPlaylistName, r: '' +new Date().getTime()},function(data){
		            currentPlaylistName = selectedPlaylistName;
		            document.getElementById('playlist-name').innerText = currentPlaylistName;
		            createPlaylistVideos(data.file_name_list, data.index);
                    mui.later(function(){
						mask.close();
					}, 300);
                }
            );
		});
    });

    function createPlaylistVideos(file_name_list, index) {
        videoFileList = document.getElementById('video-file-list');
		videoFileList.innerHTML = ''
        for (let i = 0; i < file_name_list.length; i++) {
            let li = document.createElement('li');
            li.className = 'mui-table-view-cell';
            let spanName = document.createElement('span');
            spanName.className = 'playlist-video-item-name';
            spanName.innerHTML = file_name_list[i];
            let btn = document.createElement('button');
            btn.setAttribute('videoName', file_name_list[i])

            /*if (index == i){
                btn.className = 'mui-btn mui-btn-danger fa fa-stop';
            } else {
                btn.className = 'mui-btn mui-btn-primary fa fa-play';
            }*/

            if (index == i){
                btn.className = 'mui-btn fa';
            } else {
                btn.className = 'mui-btn fa';
            }

            btn.setAttribute('videoIndex', "" + i)

            li.appendChild(spanName)
            li.appendChild(btn)
            btn.addEventListener('tap', function() {
                currentIndex = -1;
                if (hasClass(this, 'fa-play')) {
                    currentIndex = this.getAttribute('videoIndex');
                }
                mui.getJSON(
                        api_url,
                        {
                            command:'index',
                            index: currentIndex,
                            name: this.getAttribute('videoName'),
                            r: '' + new Date().getTime(),
                        },
                        function(data){
                            updatePlaylistVideoStatus(data);
                        }
                 );
                /*let btnArray = document.querySelectorAll('#video-file-list button');
                for (let j = 0 ; j < btnArray.length ; j++ ) {
                    if (currentIndex == -1 || j != this.getAttribute('videoIndex')) {
                        btnArray[j].classList.remove('fa-stop');
                        btnArray[j].classList.add('fa-play');
                        if ( j != this.getAttribute('videoIndex') ) {
                            btnArray[j].classList.remove('mui-btn-danger');
                            btnArray[j].classList.add('mui-btn-primary');
                        }
                    } else {
                        btnArray[j].classList.remove('fa-play');
                        btnArray[j].classList.add('fa-stop');
                    }
                }*/

            })
            videoFileList.appendChild(li);
        }
        updatePlaylistVideoStatus({});
    }

    function updatePlaylistVideoStatus(data) {
        if (data.index)
            currentSelectedIndex = data.index
        if (data.current_status)
            currentStatus = data.current_status
        let btnArray = document.querySelectorAll('#video-file-list button');
        for (let j = 0 ; j < btnArray.length ; j++ ) {
            if ( j != currentSelectedIndex ) {
                btnArray[j].classList.remove('fa-stop');
                btnArray[j].classList.add('fa-play');
                btnArray[j].classList.remove('mui-btn-danger');
                btnArray[j].classList.add('mui-btn-primary');
            } else {
                if (currentStatus == 'Stop' || btnArray[j].getAttribute('videoName') != playingFileName) {
                    btnArray[j].classList.remove('fa-stop');
                    btnArray[j].classList.add('fa-play');
                } else {
                    btnArray[j].classList.remove('fa-play');
                    btnArray[j].classList.add('fa-stop');
                }
                btnArray[j].classList.remove('mui-btn-primary');
                btnArray[j].classList.add('mui-btn-danger');
            }
        }
    }


    updateData();
    getAllPlaylist();

    setInterval(updateData, 500)
});