// yt_search.js
const yts = require("yt-search");

const query = process.argv.slice(2).join(" ");

yts(query, function (err, r) {
  if (err) {
    console.error(err);
    process.exit(1);
  }

  const video = r.videos.length > 0 ? r.videos[0] : null;
  if (video) {
    const result = {
      title: video.title,
      videoId: video.videoId,
      url: video.url,
      thumbnail: video.thumbnail,
    };
    console.log(JSON.stringify(result));
  } else {
    console.error("No video found");
    process.exit(1);
  }
});
