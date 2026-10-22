import * as THREE from "three";
import { OrbitControls } from "/dental_lab/static/lib/three/addons/controls/OrbitControls.js";
import { STLLoader } from "/dental_lab/static/lib/three/addons/loaders/STLLoader.js";
import { OBJLoader } from "/dental_lab/static/lib/three/addons/loaders/OBJLoader.js";

const params = new URLSearchParams(window.location.search);
const attachmentId = parseInt(params.get("id"), 10);
const fileName = params.get("name") || "";
const ext = fileName.split(".").pop().toLowerCase();

const wrap = document.getElementById("canvas-wrap");
const statusEl = document.getElementById("status");
document.getElementById("title").textContent = fileName;
document.title = fileName ? `3D - ${fileName}` : "3D Viewer";

function setStatus(text) {
    statusEl.textContent = text;
    statusEl.style.display = text ? "flex" : "none";
}

// ---- Scene -----------------------------------------------------------------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f3);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
// Dental scans (STL) are generally Z-up
camera.up.set(0, ext === "stl" ? 0 : 1, ext === "stl" ? 1 : 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
wrap.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x888899, 1.1));
const headLight = new THREE.DirectionalLight(0xffffff, 1.4);
scene.add(headLight);
scene.add(headLight.target);

let model = null;
let initialView = null;
let wireframe = false;

const material = new THREE.MeshStandardMaterial({
    color: 0xe9dfd0,
    roughness: 0.55,
    metalness: 0.05,
    side: THREE.DoubleSide,
});

function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

function fitCameraToModel(object) {
    const box = new THREE.Box3().setFromObject(object);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const dist = (maxDim / 2) / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.8;

    // Put the model's center at the origin
    object.position.sub(center);

    const dir = new THREE.Vector3(1, -1, 0.8).normalize();
    if (ext !== "stl") {
        dir.set(1, 0.8, 1).normalize();
    }
    camera.position.copy(dir.multiplyScalar(dist));
    camera.near = maxDim / 1000;
    camera.far = maxDim * 100;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();

    initialView = { position: camera.position.clone(), target: controls.target.clone() };
}

function applyMaterial(object) {
    object.traverse((child) => {
        if (child.isMesh) {
            if (!child.geometry.attributes.normal) {
                child.geometry.computeVertexNormals();
            }
            child.material = material;
        }
    });
}

async function load() {
    if (!attachmentId || !["stl", "obj"].includes(ext)) {
        setStatus("Unsupported file or missing attachment id.");
        return;
    }
    const url = `/web/content/${attachmentId}?download=false`;
    const resp = await fetch(url, { credentials: "same-origin" });
    if (!resp.ok) {
        setStatus(`Could not load the file (HTTP ${resp.status}).`);
        return;
    }
    if (ext === "stl") {
        const geometry = new STLLoader().parse(await resp.arrayBuffer());
        geometry.computeVertexNormals();
        model = new THREE.Mesh(geometry, material);
    } else {
        model = new OBJLoader().parse(await resp.text());
        applyMaterial(model);
    }
    scene.add(model);
    fitCameraToModel(model);
    setStatus("");
}

load().catch((err) => {
    console.error(err);
    setStatus("Failed to display the 3D model.");
});

// ---- Toolbar ----------------------------------------------------------------
document.getElementById("btn-reset").addEventListener("click", () => {
    if (!initialView) {
        return;
    }
    camera.position.copy(initialView.position);
    controls.target.copy(initialView.target);
    controls.update();
});
document.getElementById("btn-wire").addEventListener("click", () => {
    wireframe = !wireframe;
    material.wireframe = wireframe;
});

// ---- Loop -------------------------------------------------------------------
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    headLight.position.copy(camera.position);
    renderer.render(scene, camera);
}
animate();