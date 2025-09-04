"use client";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

export default function STLViewer({ url }: { url: string }) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0f14);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
    camera.position.set(150, 120, 160);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const light = new THREE.DirectionalLight(0xffffff, 1.0);
    light.position.set(1, 1, 1);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0xffffff, 0.4));

    const grid = new THREE.GridHelper(400, 40, 0x666666, 0x333333);
    grid.position.y = -1;
    scene.add(grid);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controlsRef.current = controls;

    let mesh: THREE.Mesh | null = null;

    const loader = new STLLoader();
    loader.load(
      url,
      (geometry) => {
        geometry.computeBoundingBox();
        geometry.center();
        const material = new THREE.MeshStandardMaterial({ color: 0xdddddd, metalness: 0.1, roughness: 0.6 });
        mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        // Auto-scale & frame
        const bb = geometry.boundingBox!;
        const size = new THREE.Vector3();
        bb.getSize(size);
        const fitDistance = Math.max(size.x, size.y, size.z) * 2.0;
        const dir = new THREE.Vector3(1, 1, 1).normalize();
        camera.position.copy(dir.multiplyScalar(fitDistance));
        camera.lookAt(0, 0, 0);
        controls.target.set(0, 0, 0);
        controls.update();
      },
      undefined,
      (err) => {
        console.error("STL load error", err);
      }
    );

    const handleResize = () => {
      if (!mountRef.current) return;
      const { clientWidth, clientHeight } = mountRef.current;
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(clientWidth, clientHeight);
    };
    window.addEventListener("resize", handleResize);

    const tick = () => {
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    };
    tick();

    return () => {
      window.removeEventListener("resize", handleResize);
      controls.dispose();
      if (mesh) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      renderer.dispose();
      mountRef.current?.removeChild(renderer.domElement);
    };
  }, [url]);

  return <div ref={mountRef} className="w-full h-full" />;
}
