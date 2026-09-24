"""M7: dataset presets, label mapping and per-image metrics of tools/dataset.py (no model, no download)."""

import csv

import pytest

from edge_agent.config import load_thresholds
from tools import dataset as ds
from tools.dataset import Preset, Sample, Signal


def make_tree(root, files):
    for rel in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")


def preset(**kw):
    base = {"name": "p", "kaggle": "o/s", "task": "eye_state", "positive": "closed", "classes": {"closed": "closed"}}
    base.update(kw)
    return Preset(**base)


# ---------------------------------------------------------------- presets


def test_bundled_presets_load_and_are_consistent():
    presets = ds.load_presets()
    assert {"mrl_eye", "yawn_eye_mouth", "state_farm", "yawdd"} <= set(presets)
    for pr in presets.values():
        assert pr.positive in pr.classes.values(), pr.name
        assert pr.input in ("face", "eye_crop") and pr.label_from in ("folder", "stem_suffix")
        assert all(k == k.lower() for k in pr.classes)  # matched case-insensitively


def test_unknown_task_is_refused(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("x: {kaggle: a/b, task: sleepy, positive: a, classes: {a: a}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown task"):
        ds.load_presets(p)


# ---------------------------------------------------------------- files -> labels


def test_folder_labels_split_and_deepest_folder(tmp_path):
    make_tree(
        tmp_path,
        [
            "dataset_new/test/Closed/_1.jpg",
            "dataset_new/test/Open/_1.jpg",
            "dataset_new/train/Closed/_2.jpg",  # other split: skipped
            "dataset_new/test/yawn/3.jpg",  # class not in this preset: skipped
            "dataset_new/test/Open/notes.txt",  # not an image
        ],
    )
    pr = preset(split="test", classes={"closed": "closed", "open": "open"})
    samples = ds.collect_samples(tmp_path, pr)
    assert [(s.path.name, s.label, s.group) for s in samples] == [
        ("_1.jpg", "closed", "closed"),
        ("_1.jpg", "open", "open"),
    ]


def test_state_farm_groups_map_to_two_labels(tmp_path):
    make_tree(tmp_path, ["imgs/train/c0/a.jpg", "imgs/train/c1/b.jpg", "imgs/train/c6/c.jpg", "imgs/test/d.jpg"])
    pr = ds.load_presets()["state_farm"]
    samples = ds.collect_samples(tmp_path, pr)
    assert sorted((s.group, s.label) for s in samples) == [("c0", "no_phone"), ("c1", "phone"), ("c6", "no_phone")]


def test_yawdd_stem_suffix_labels(tmp_path):
    make_tree(
        tmp_path,
        [
            "Mirror/Mirror/Female_mirror/1-FemaleNoGlasses-Yawning.avi",
            "Mirror/Mirror/Female_mirror/1-FemaleNoGlasses-Talking.avi",
            "Mirror/Mirror/Male_mirror Avi Videos/3-MaleGlasses-TalkingYawning.avi",
            "Dash/Dash/Female/1-FemaleNoGlasses.avi",  # not in the Mirror split
            "Readme_YawDD.pdf",
        ],
    )
    samples = ds.collect_samples(tmp_path, ds.load_presets()["yawdd"])
    assert sorted((s.path.name, s.label) for s in samples) == [
        ("1-FemaleNoGlasses-Talking.avi", "none"),
        ("1-FemaleNoGlasses-Yawning.avi", "yawn"),
        ("3-MaleGlasses-TalkingYawning.avi", "yawn"),
    ]


def test_limit_takes_evenly_spaced_files_per_class(tmp_path):
    make_tree(tmp_path, [f"Closed/{i:02d}.jpg" for i in range(10)] + ["Open/a.jpg"])
    pr = preset(classes={"closed": "closed", "open": "open"})
    samples = ds.collect_samples(tmp_path, pr, limit_per_class=5)
    assert [s.path.name for s in samples if s.label == "closed"] == ["00.jpg", "02.jpg", "04.jpg", "06.jpg", "08.jpg"]
    assert [s.path.name for s in samples if s.label == "open"] == ["a.jpg"]


# ---------------------------------------------------------------- metrics


def test_confusion_and_none_is_negative():
    sig = Signal("ear", 0.2, higher_is_positive=False, scores=[0.1, 0.3, None, 0.15])
    pred = ds.predict(sig, sig.threshold)
    assert pred == [True, False, False, True]
    m = ds.confusion(pred, [True, False, True, False])
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5 and m["accuracy"] == 0.5


def test_sweep_finds_separating_threshold():
    sig = Signal("mar", 0.9, True, scores=[0.2, 0.3, 0.7, 0.8])
    truth = [False, False, True, True]
    assert ds.confusion(ds.predict(sig, sig.threshold), truth)["recall"] == 0.0  # configured value too high
    thr, m = ds.best_threshold(ds.sweep(sig, truth))
    assert 0.3 < thr <= 0.7 and m["f1"] == 1.0
    assert ds.best_threshold(ds.sweep(Signal("x", 1, True, [None]), [True])) is None


def test_best_threshold_does_not_pick_everything_positive():
    # weak signal on a balanced set: "all positive" has F1 0.67 but is no better than chance
    sig = Signal("weak", 0.9, True, scores=[0.1, 0.2, 0.3, 0.4, 0.15, 0.25, 0.35, 0.8])
    truth = [False, False, False, False, True, True, True, True]
    thr, m = ds.best_threshold(ds.sweep(sig, truth))
    assert m["specificity"] > 0 and thr > 0.1


def test_drowsy_proxy_uses_ear_and_mar_margins():
    th = load_thresholds()
    sigs = ds.make_signals(ds.load_presets()["ddd"], th)
    ds.fill_signals(sigs, {"ear": 0.1, "mar": 0.2, "p_closed": 0.9})  # eyes closed
    ds.fill_signals(sigs, {"ear": 0.3, "mar": 0.9, "p_closed": 0.1})  # yawning
    ds.fill_signals(sigs, {"ear": 0.3, "mar": 0.2, "p_closed": 0.1})  # alert
    ds.fill_signals(sigs, {"face": False})  # no face
    proxy = sigs[-1]
    assert ds.predict(proxy, proxy.threshold) == [True, True, False, False]


def test_report_shows_per_group_rates():
    pr = ds.load_presets()["state_farm"]
    samples = [
        Sample(ds.Path(f"{g}.jpg"), lab, g) for g, lab in (("c0", "no_phone"), ("c1", "phone"), ("c6", "no_phone"))
    ]
    sigs = ds.make_signals(pr, load_thresholds())
    for m in (
        {"phone_zone": 0.1, "phone_any": 0.1},
        {"phone_zone": 0.9, "phone_any": 0.9},
        {"phone_zone": None, "phone_any": 0.5},
    ):
        ds.fill_signals(sigs, m)
    text = ds.report(pr, samples, sigs, [True, True, False])
    assert "| c6 | no_phone | 1 | 0.0% | 100.0% |" in text  # a hard negative the zone rule filters out
    assert "Best threshold" in text and "Face found" in text


# ---------------------------------------------------------------- video presets


def test_clip_label_rows_feed_eval_py(tmp_path):
    from tools import eval as ev

    pr = ds.load_presets()["yawdd"]
    a, b = tmp_path / "m" / "1-F-Yawning.avi", tmp_path / "m" / "1-F-Normal.avi"
    samples = [Sample(a, "yawn", "yawning"), Sample(b, "none", "normal")]
    rows = ds.clip_label_rows(pr, samples, tmp_path, {"m/1-F-Yawning.avi": 30.0, "m/1-F-Normal.avi": 20.0})
    out = tmp_path / "labels.csv"
    ds.write_labels(out, rows)
    episodes, videos = ev.read_labels(out)
    assert videos == ["m/1-F-Yawning.avi", "m/1-F-Normal.avi"]
    assert episodes == [ev.Episode("m/1-F-Yawning.avi", "yawn", 0.0, 30.0)]
    assert list(csv.reader(out.open(encoding="utf-8")))[2] == ["m/1-F-Normal.avi", "none", "", ""]
