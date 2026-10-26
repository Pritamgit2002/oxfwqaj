// Turns the recorded walkthrough (demo/out) into the README assets in docs/demo:
//   windsight-demo.mp4  H.264 with burned-in subtitles plus a soft English subtitle track
//   windsight-demo.srt / .vtt  the same subtitles as sidecar files
//   windsight-demo.gif  silent preview that GitHub renders inline
// Requires ffmpeg with libx264 on PATH.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const here = import.meta.dirname;
const out = path.join(here, "out");
const docs = path.resolve(here, "../../../docs/demo");
mkdirSync(docs, { recursive: true });

// Cue times are relative to the title card; the page-load frames before it are trimmed off.
const { trimMs, cues } = JSON.parse(readFileSync(path.join(out, "captions.json"), "utf8"));

const stamp = (ms, sep) => {
  const pad = (n, w = 2) => String(Math.floor(n)).padStart(w, "0");
  return `${pad(ms / 3_600_000)}:${pad((ms / 60_000) % 60)}:${pad((ms / 1000) % 60)}${sep}${pad(ms % 1000, 3)}`;
};

const srt = cues
  .map((c, i) => `${i + 1}\n${stamp(c.start, ",")} --> ${stamp(c.end, ",")}\n${c.text}\n`)
  .join("\n");
const vtt = `WEBVTT\n\n${cues
  .map((c) => `${stamp(c.start, ".")} --> ${stamp(c.end, ".")}\n${c.text}\n`)
  .join("\n")}`;

const file = (ext) => path.join(docs, `windsight-demo.${ext}`);
writeFileSync(file("srt"), srt);
writeFileSync(file("vtt"), vtt);

const ffmpeg = (...args) =>
  execFileSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], {
    stdio: "inherit",
  });

ffmpeg(
  "-ss",
  String(trimMs / 1000),
  "-i",
  path.join(out, "raw.webm"),
  "-i",
  file("srt"),
  "-map",
  "0:v",
  "-map",
  "1:s",
  "-c:v",
  "libx264",
  "-preset",
  "slow",
  "-crf",
  "20",
  "-pix_fmt",
  "yuv420p",
  "-r",
  "25",
  "-c:s",
  "mov_text",
  "-metadata:s:s:0",
  "language=eng",
  "-metadata:s:s:0",
  "title=English",
  "-movflags",
  "+faststart",
  file("mp4"),
);

ffmpeg(
  "-i",
  file("mp4"),
  "-vf",
  "fps=4,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
  file("gif"),
);

const seconds = (cues.at(-1)?.end ?? 0) / 1000;
console.log(
  `demo: ${cues.length} subtitles, ${seconds.toFixed(0)} s -> ${path.relative(process.cwd(), docs)}`,
);
