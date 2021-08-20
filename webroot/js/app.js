mui.init();
mui.ready(function() {
    
    device_key = '{device_key}';
    
    let global = {
        apiUrl: '../api/' + device_key,
        isSeeking: false,
        chimee: undefined,
        isLocal: false,
        currentPlaylist: { name: '', index: -1, },
        currentVideo: { path: '', name: '', position: -1, duration: -1, },
        dlnaPlayer: { occupied: false, status: "", },
        viewPlaylist: { name: '', index: -1, position: -1, videoList: [], },
    };

    let playListPicker = new mui.PopPicker();

    let mask = mui.createMask();

    // 圆形进度条
    circleProgress = new CircleProgress('.circle-progress-content')
        .attr('max', 100)
        .attr('value', 0)
        .attr('animationDuration', 0)
        .attr('textFormat', function(value, max) {
            if(global.dlnaPlayer.status == 'Play') {
                return '&#xf04c';
			} else if (global.dlnaPlayer.status == 'Pause' || global.dlnaPlayer.status == 'Stop') {
				return '&#xf04b';
			}
			return '&#xf04b';
		});

	mui('#circle-progress-wrapper').on('click', '.circle-progress-content', function(){
		if(global.dlnaPlayer.status == 'Play') {
			global.dlnaPlayer.status = 'Pause';
			mui.getJSON(global.apiUrl,{command:'pause', r: '' +new Date().getTime()},function(data){});
		} else if (global.dlnaPlayer.status == 'Pause') {
		    global.dlnaPlayer.status = 'Play';
		    mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()},function(data){});
		} else if (global.dlnaPlayer.status = 'Stop') {
            mui.getJSON(global.apiUrl,
                        {
                            command:'index',
                            r: '' +new Date().getTime(),
                            index: global.currentPlaylist.index,
                            name: global.currentVideo.name,
                        },
                        function(data){}
                    );
        }
	})

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
        +formatTime(global.currentVideo.position)
        + (t == 0 ? '' : '(' + formatTime(global.currentVideo.position + t)  + ')');
    }
    updateSeekInfo(0);
    let seekBtnFunc = function() {
    	if (global.isLocal) {
	        return;
	    }
        global.isSeeking = true
        offset += parseInt(this.getAttribute('timeOffset'));
        if ((offset < 0) && (global.currentVideo.position + offset < 0) ) {
            offset = -global.currentVideo.position;
        } else if (offset + global.currentVideo.position > global.currentVideo.duration) {
            offset = global.currentVideo.duration - global.currentVideo.position;
        }
		updateSeekInfo(offset);
	};
	let seekBtnEndFunc = debounce(function() {
	    if (global.isLocal) {
	        return;
	    }
	    mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        global.isSeeking = false;
	    }, 1000);
	}, 1000);

	let offsetBtns = document.querySelectorAll('.timeSeekButton')
	for (let ob of offsetBtns) {
		ob.addEventListener('click', seekBtnFunc);
		ob.addEventListener('click', seekBtnEndFunc);
	}

    let startPos = 0
    let progressBar = document.getElementById('progressBar');
    let rangeSeekStartFunc = function(){
        startPos = global.currentVideo.position;
        global.isSeeking = true;
    }

	let rangeSeekFunc = function() {
	    offset = progressBar.value - startPos;
	    updateSeekInfo(offset);
	};
	let rangeSeekEndFunc =function() {
	    mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    startPos = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        global.isSeeking = false;
	    }, 1000);

	};

	progressBar.min = 0;
	progressBar.max = global.currentVideo.duration;
	progressBar.addEventListener('mousedown', rangeSeekStartFunc);
	progressBar.addEventListener('touchstart', rangeSeekStartFunc);
	progressBar.addEventListener('input', rangeSeekFunc);
	progressBar.addEventListener('mouseup', rangeSeekEndFunc);
	progressBar.addEventListener('touchend', rangeSeekEndFunc);

    //数据更新
    function updateData() {
        if (global.isLocal)
            return;
        if (!global.isSeeking) {
            mui.getJSON(global.apiUrl,{command:'status', r: '' +new Date().getTime()},function(data){

                    if (!global.isSeeking) {

                        playlist_changed = global.viewPlaylist.name != data.viewPlaylist.name;
                        current_video_changed =global.currentVideo.path != data.currentVideo.path;
                        video_position_changed = global.currentVideo.position != data.currentVideo.position;
                        player_status_changed = global.dlnaPlayer.status != data.dlnaPlayer.status;
                        occupied_status_changed = global.dlnaPlayer.occupied != data.dlnaPlayer.occupied;
                        video_duration_changed = global.currentVideo.duration != data.currentVideo.duration;

                        let old = {};
                        old.currentPlaylist = global.currentPlaylist;
                        old.currentVideo = global.currentVideo;
                        old.dlnaPlayer = global.dlnaPlayer;
                        old.viewPlaylist = global.viewPlaylist;

                        global.currentPlaylist = data.currentPlaylist;
                        global.currentVideo = data.currentVideo;
                        global.dlnaPlayer = data.dlnaPlayer;
                        global.viewPlaylist = data.viewPlaylist;

                        if (player_status_changed) {
                            if (data.dlnaPlayer.status == 'Stop') {
                                document.getElementById('stopVideo').disabled = true;
                            } else {
                                document.getElementById('stopVideo').disabled = false;
                            }
                        }

                        if (occupied_status_changed || player_status_changed) {
                            let txtStatus = document.getElementById('playerStatus')
                            if(data.dlnaPlayer.occupied)
                                txtStatus.innerHTML = '投屏被占用';
                            else if (data.dlnaPlayer.status == 'Stop')
                                txtStatus.innerHTML = '已停止投屏';
                            else if (data.dlnaPlayer.status == 'Pause')
                                txtStatus.innerHTML = '投屏已暂停';
                            else if (data.dlnaPlayer.status == 'Play')
                                txtStatus.innerHTML = '正在播放';
                        }
                        if (current_video_changed)
                            document.getElementById('currentFileName').innerHTML = data.currentVideo.name;

                        if (playlist_changed) {
                            document.getElementById('playlist-name').innerText = data.viewPlaylist.name;
                            createPlaylistVideos(data.viewPlaylist.videoList, data.viewPlaylist.index);
                        }

                        if (video_duration_changed || player_status_changed){
                            circleProgress.attr({ max: data.currentVideo.duration, });
                            progressBar.max = global.currentVideo.duration;
                        }

                        if (video_position_changed || player_status_changed) {
                            circleProgress.attr({ value: data.currentVideo.position, });
                            progressBar.value = data.currentVideo.position;
                            timeInfoText = formatTime(data.currentVideo.position) + '/' + formatTime(data.currentVideo.duration);
                            document.getElementById('timeInfo').innerText = timeInfoText;
                            updateSeekInfo(0);
                        }

                        if (current_video_changed || playlist_changed || player_status_changed) {
                            updatePlaylistVideoStatus(data);
                        }

                    }

                }
            );
        }

    }

    //获取播放列表
    function getAllPlaylist() {
        mui.getJSON(global.apiUrl,{command:'getAllPlaylist', r: '' +new Date().getTime()}, function(data){
            console.log(data);
            let pickerData = new Array();
            for(let i = 0; i < data.length; i++) {
                pickerData[i] = {
                    value: data[i],
                    text: data[i]
                }
            }
            playListPicker.setData(pickerData);
        });
    }

    mui('#morePlaylist')[0].addEventListener('tap', function(){
		playListPicker.pickers[0].setSelectedValue(global.viewPlaylist.name, 1000)
		playListPicker.show(function(items) {
		    selectedPlaylistName = items[0].value
		    if (selectedPlaylistName == global.viewPlaylist.name) {
		        return
		    }
		    mask.show();
		    mui.getJSON(global.apiUrl,{command:'switchPlayList', o: '', n: selectedPlaylistName, r: '' +new Date().getTime()},function(data){
		            global.viewPlaylist = data.viewPlaylist;
		            document.getElementById('playlist-name').innerText = global.viewPlaylist.name;
		            createPlaylistVideos(global.viewPlaylist.videoList, global.viewPlaylist.index);
                    mui.later(function(){
						mask.close();
					}, 300);
                }
            );
		});
    });

    document.getElementById('stopVideo').addEventListener('click', function() {
        mui.getJSON(global.apiUrl,{command:'stop', r: '' +new Date().getTime()},function(data){});
        this.disabled = true;
    });

    document.getElementById('playLocal').addEventListener('click', function() {

        function updateButton(enable) {
            document.getElementById('stopVideo').disabled = enable;
            document.getElementById('progressBar').disabled = enable;
            document.getElementById('morePlaylist').disabled = enable;

            [].forEach.call(document.querySelectorAll('.timeSeekButton'), function(btn) {
              btn.disabled = enable;
            });
            [].forEach.call(document.querySelectorAll('#video-file-list > li > button'), function(btn) {
              btn.disabled = enable;
            });
        }

        thisElement = this;

        if (hasClass(this, 'fa-arrow-circle-left')) {
            mask.show();
            global.isLocal = false;
            let pos = parseInt(global.chimee.currentTime);
            let offset = parseInt(global.chimee.currentTime - global.currentPosition);
            global.chimee.destroy();
            mui.getJSON(global.apiUrl,{command:'backToDlna', pos: pos - 3,  r: '' +new Date().getTime()},function(data){
                thisElement.classList.add('fa-play-circle-o');
                thisElement.classList.remove('fa-arrow-circle-left');
                thisElement.innerText = '本机播放';
                document.getElementById('circleProgress').style.display = '';
                document.getElementById('videoPlayer').style.display = 'none';
                updateButton(false);
                mui.later(function(){
                    mask.close();
                }, 100);
            });
        } else if (hasClass(this, 'fa-play-circle-o')) {
            mask.show();
            document.getElementById('circleProgress').style.display = 'none';
            document.getElementById('videoPlayer').style.display = '';
            global.isLocal = true;
            global.chimee = new ChimeeMobilePlayer({
				wrapper: '#videoPlayer',
				controls: true,
				autoplay: true,
				x5VideoPlayerFullscreen: true,
				x5VideoOrientation: 'portrait',
				xWebkitAirplay: true,
				width:'100%',
				height:'100%',
			});
            flag = -1;
            global.chimee.on('timeupdate', function(){
                if (flag == -1 && global.chimee.currentTime > 0.3) {
                    flag = 1;
                    global.chimee.currentTime = global.currentVideo.position - 3;
                }
			});
			mui.getJSON(global.apiUrl,{command:'pause', r: '' +new Date().getTime()},function(data){
                global.chimee.load(global.apiUrl + '?command=playAtApp&r=' + new Date().getTime());
                thisElement.classList.remove('fa-play-circle-o');
                thisElement.classList.add('fa-arrow-circle-left');
                thisElement.innerText = '返回投屏';
                updateButton(true);
                mui.later(function(){
					mask.close();
				}, 300);
			});

        }
    });

    document.getElementById('buttonPlaylistMenu').addEventListener('tap', function() {
        setTimeout(function(){
            var targetEle = document.querySelector('ul#video-file-list li button.mui-btn.fa.mui-btn-danger');
            zenscroll.center(targetEle, 0)
        }, 1);

    });

    function createPlaylistVideos(file_name_list, index) {
        videoFileList = document.getElementById('video-file-list');
		videoFileList.innerHTML = '';
        for (let i = 0; i < file_name_list.length; i++) {
            let li = document.createElement('li');
            li.className = 'mui-table-view-cell';
            let spanName = document.createElement('span');
            spanName.className = 'playlist-video-item-name';
            spanName.innerHTML = file_name_list[i];
            let btn = document.createElement('button');
            btn.setAttribute('videoName', file_name_list[i])
            btn.className = 'mui-btn fa';
            btn.setAttribute('videoIndex', "" + i)

            li.appendChild(spanName);
            li.appendChild(btn);
            btn.addEventListener('tap', function() {
                currentIndex = -1;
                if (hasClass(this, 'fa-play')) {
                    currentIndex = this.getAttribute('videoIndex');
                }
                mui.getJSON(
                        global.apiUrl,
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
            })
            videoFileList.appendChild(li);
        }
        updatePlaylistVideoStatus({});
    }

    function updatePlaylistVideoStatus(data) {
        if (data.viewPlaylist && data.viewPlaylist.index)
            global.viewPlaylist.index = data.viewPlaylist.index;
        if (data.dlnaPlayer && data.dlnaPlayer.status)
            global.dlnaPlayer.status = data.dlnaPlayer.status;
        let btnArray = document.querySelectorAll('#video-file-list button');
        for (let j = 0 ; j < btnArray.length ; j++ ) {
            if ( j != global.viewPlaylist.index ) {
                btnArray[j].classList.remove('fa-stop');
                btnArray[j].classList.add('fa-play');
                btnArray[j].classList.remove('mui-btn-danger');
                btnArray[j].classList.add('mui-btn-primary');
            } else {
                if(global.currentPlaylist.name != global.viewPlaylist.name) {
                    btnArray[j].classList.remove('fa-stop');
                    btnArray[j].classList.add('fa-play');
                } else if (global.dlnaPlayer.status == 'Stop' || btnArray[j].getAttribute('videoName') != global.currentVideo.name) {
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