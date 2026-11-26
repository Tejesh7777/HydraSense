/**
 * Three.js Interactive 3D Cluster Visualizer for Greywater Analysis
 * SIH26023 Objective 2: 3D similarity-based grouping visualization.
 */

class Greywater3DVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.pointsGroup = null;
        this.centroidsGroup = null;
        this.gridHelper = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredObject = null;
        this.autoRotate = false;
        this.pointMeshes = [];
        this.animationFrameId = null;

        this.init();
    }

    init() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x060c1b, 0.035);

        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        this.camera.position.set(18, 14, 22);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x060c1b, 0.85);
        this.container.appendChild(this.renderer.domElement);

        if (typeof THREE.OrbitControls !== 'undefined') {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.06;
            this.controls.maxDistance = 80;
            this.controls.minDistance = 5;
        }

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0x00f0ff, 1.2);
        dirLight1.position.set(20, 30, 20);
        this.scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0x0088ff, 0.8);
        dirLight2.position.set(-20, -20, -20);
        this.scene.add(dirLight2);

        const grid = new THREE.GridHelper(30, 20, 0x00f0ff, 0x0c254d);
        grid.position.y = -8;
        this.scene.add(grid);
        this.gridHelper = grid;

        const boxGeo = new THREE.BoxGeometry(26, 20, 26);
        const boxMat = new THREE.MeshBasicMaterial({
            color: 0x00f0ff,
            wireframe: true,
            transparent: true,
            opacity: 0.12
        });
        const boxMesh = new THREE.Mesh(boxGeo, boxMat);
        boxMesh.position.y = 2;
        this.scene.add(boxMesh);

        this.pointsGroup = new THREE.Group();
        this.centroidsGroup = new THREE.Group();
        this.scene.add(this.pointsGroup);
        this.scene.add(this.centroidsGroup);

        window.addEventListener('resize', () => this.onResize());
        this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.renderer.domElement.addEventListener('click', (e) => this.onClick(e));

        this.animate();
    }

    onResize() {
        if (!this.container || !this.renderer || !this.camera) return;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    onMouseMove(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycastCheck();
    }

    onClick(event) {
        if (this.hoveredObject && this.hoveredObject.userData) {
            const data = this.hoveredObject.userData;
            if (window.onSelect3DSample) {
                window.onSelect3DSample(data);
            }
        }
    }

    raycastCheck() {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.pointMeshes);

        const tooltip = document.getElementById('cluster-3d-tooltip');

        if (intersects.length > 0) {
            const hit = intersects[0].object;
            if (this.hoveredObject !== hit) {
                if (this.hoveredObject) {
                    this.hoveredObject.scale.set(1, 1, 1);
                }
                this.hoveredObject = hit;
                hit.scale.set(1.7, 1.7, 1.7);
            }

            if (tooltip && hit.userData) {
                const d = hit.userData;
                tooltip.style.display = 'block';
                tooltip.innerHTML = `
                    <div class="node-tooltip-title">
                        <span>${d.id}</span>
                        <span style="color:${d.color}; font-size:0.75rem;">Cluster ${d.cluster}</span>
                    </div>
                    <div style="font-size:0.76rem; color:var(--text-muted); margin-bottom:4px;">${d.source}</div>
                    <div class="node-tooltip-grid">
                        <div><span>pH:</span> <strong>${d.pH}</strong></div>
                        <div><span>TDS:</span> <strong>${d.TDS} mg/L</strong></div>
                        <div><span>BOD:</span> <strong>${d.BOD} mg/L</strong></div>
                        <div><span>COD:</span> <strong>${d.COD} mg/L</strong></div>
                        <div><span>Turbidity:</span> <strong>${d.Turbidity} NTU</strong></div>
                        <div><span>EC:</span> <strong>${d.EC} µS/cm</strong></div>
                        <div><span>TSS:</span> <strong>${d.TSS} mg/L</strong></div>
                        <div><span>Oil & Grease:</span> <strong>${d.Oil_and_Grease} mg/L</strong></div>
                    </div>
                    <div style="margin-top:8px; font-size:0.72rem; color:var(--cyan-primary);">
                        Category: <strong>${d.category}</strong>
                    </div>
                `;
            }
        } else {
            if (this.hoveredObject) {
                this.hoveredObject.scale.set(1, 1, 1);
                this.hoveredObject = null;
            }
            if (tooltip) {
                tooltip.style.display = 'none';
            }
        }
    }

    loadData(payload3d) {
        if (!payload3d) return;

        // Clear existing
        while (this.pointsGroup.children.length > 0) {
            this.pointsGroup.remove(this.pointsGroup.children[0]);
        }
        while (this.centroidsGroup.children.length > 0) {
            this.centroidsGroup.remove(this.centroidsGroup.children[0]);
        }
        this.pointMeshes = [];

        const points = payload3d.points || [];
        const centroids = payload3d.centroids || [];

        // Scaling factor for PCA space coordinates
        const scaleXYZ = 3.2;

        // 1. Render Sample Points
        const pointGeo = new THREE.SphereGeometry(0.35, 16, 16);

        points.forEach((pt) => {
            const colorHex = parseInt(pt.color.replace('#', '0x'));
            const pointMat = new THREE.MeshPhongMaterial({
                color: colorHex,
                emissive: colorHex,
                emissiveIntensity: 0.35,
                shininess: 90
            });

            const mesh = new THREE.Mesh(pointGeo, pointMat);
            mesh.position.set(pt.x * scaleXYZ, pt.y * scaleXYZ, pt.z * scaleXYZ);
            mesh.userData = pt;

            this.pointsGroup.add(mesh);
            this.pointMeshes.push(mesh);
        });

        // 2. Render Centroids with Glowing Orbital Rings
        centroids.forEach((c) => {
            const colorHex = parseInt(c.color.replace('#', '0x'));

            // Core centroid sphere
            const cGeo = new THREE.SphereGeometry(0.85, 24, 24);
            const cMat = new THREE.MeshStandardMaterial({
                color: colorHex,
                emissive: colorHex,
                emissiveIntensity: 0.8,
                roughness: 0.2
            });
            const cMesh = new THREE.Mesh(cGeo, cMat);
            cMesh.position.set(c.x * scaleXYZ, c.y * scaleXYZ, c.z * scaleXYZ);

            // Orbiting wireframe halo ring
            const ringGeo = new THREE.TorusGeometry(1.6, 0.05, 8, 32);
            const ringMat = new THREE.MeshBasicMaterial({
                color: colorHex,
                wireframe: true,
                transparent: true,
                opacity: 0.7
            });
            const ringMesh = new THREE.Mesh(ringGeo, ringMat);
            ringMesh.rotation.x = Math.PI / 3;
            cMesh.add(ringMesh);

            this.centroidsGroup.add(cMesh);
        });
    }

    resetCamera() {
        if (!this.camera || !this.controls) return;
        this.camera.position.set(18, 14, 22);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }

    toggleAutoRotate() {
        this.autoRotate = !this.autoRotate;
        if (this.controls) {
            this.controls.autoRotate = this.autoRotate;
            this.controls.autoRotateSpeed = 1.4;
        }
        return this.autoRotate;
    }

    animate() {
        this.animationFrameId = requestAnimationFrame(() => this.animate());

        if (this.controls) {
            this.controls.update();
        }

        // Slowly rotate centroid rings
        this.centroidsGroup.children.forEach((cMesh) => {
            if (cMesh.children.length > 0) {
                cMesh.children[0].rotation.z += 0.02;
            }
        });

        this.renderer.render(this.scene, this.camera);
    }
}
