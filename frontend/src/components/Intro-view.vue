<template>
  <div class="intro-container">
    <!-- 左侧 Attribution Selection -->
    <div class="left-panel">
      <div class="header-section">
        <h2>Attribution(s) Focus View</h2>
      </div>
      <div class="attribution-options">
        <div 
          v-for="attr in attributions" 
          :key="attr"
          class="option-card"
          :style="{ 
            backgroundColor: customColors[attr],
            borderColor: darkenColor(customColors[attr])
          }"
        >
          <label>
            <input 
              type="checkbox" 
              v-model="selectedAttributions" 
              :value="attr"
              :style="{ accentColor: darkenColor(customColors[attr]) }"
            />
            <span class="option-text">{{ attr }}</span>
          </label>
        </div>
      </div>
      <button @click="goToSelectedView">Proceed to Attribution(s) Focus View</button>
    </div>

    <!-- 右侧 Main View -->
    <div class="right-panel">
      <div class="header-section">
        <h2>Complete Network View</h2>
        <img 
          src="@/assets/main-view-image.jpg" 
          alt="Main View Illustration"
          class="main-view-image"
        />
      </div>
      <button @click="goToMainView">Proceed to Complete Network View</button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      userId: '',
      attributions: [
        "responsibility", "fear and dangerousness", "anger", "no pity",
        "social distance", "no help", "coercion segregation", "no responsibility",
        "no fear and dangerousness", "no anger", "pity", "help",
        "no social distance", "no coercion segregation"
      ],
      selectedAttributions: [],
      customColors: {
        "responsibility": "#F5B7B1",
        "fear and dangerousness": "#D7BDE2",
        "anger": "#D7BDE2",
        "no pity": "#D7BDE2",
        "social distance": "#ADD8E6",
        "no help": "#ADD8E6",
        "coercion segregation": "#ADD8E6",
        "no responsibility": "#D98880",
        "no fear and dangerousness": "#BB8FCE",
        "no anger": "#BB8FCE",
        "pity": "#BB8FCE",
        "help": "#87CEEB",
        "no social distance": "#87CEEB",
        "no coercion segregation": "#87CEEB"
      }
    };
  },

  mounted() {
    this.userId = this.$route.query.userId;
  },

  methods: {
    darkenColor(hex) {
      let r = parseInt(hex.substring(1,3),16);
      let g = parseInt(hex.substring(3,5),16);
      let b = parseInt(hex.substring(5,7),16);
      return `rgb(${Math.max(r-30,0)},${Math.max(g-30,0)},${Math.max(b-30,0)})`;
    },
    
    goToSelectedView() {
      if (this.selectedAttributions.length === 0) {
        alert("Please select at least one attribution.");
        return;
      }

      this.$router.push({
        name: "SelectedView",
        query: { 
          userId: this.userId,
          attributions: this.selectedAttributions.join(",")
        }
      });
    },

    goToMainView() {
      this.$router.push({ 
        name: "Main",
        query: { 
          userId: this.userId
        } 
      });
    }
  }
};
</script>

<style scoped>
.intro-container {
  display: flex;
  width: 100%;
  height: 100vh;
}

.header-section {
  position: relative;
  top: 0;
  width: 100%;
  padding: 20px 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.left-panel, .right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  padding: 20px;
}

.left-panel {
  background-color: #ECFDF1;
  border-right: 2px solid #ccc;
}

.right-panel {
  background-color: #FEE7E6;
}

.attribution-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin: 20px 0;
  max-width: 800px;
  padding: 10px;
}

.option-card {
  padding: 10px;
  border-radius: 8px;
  border: 2px solid;
  transition: transform 0.2s;
  min-height: 40px;
  display: flex;
  align-items: center;
}

.option-card:hover {
  transform: translateY(-3px);
}

.option-card label {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  cursor: pointer;
}

.option-text {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: #333;
}

input[type="checkbox"] {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

button {
  padding: 12px 24px;
  font-size: 16px;
  color: #2c3e50;
  background-color: #f8f9fa; /* 浅灰色背景 */
  border: 1px solid #dee2e6; /* 添加边框 */
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  position: absolute;
  bottom: 20px;
  width: 600px;
}

button:hover {
  background-color: #e9ecef; /* 悬停加深 */
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.main-view-image {
  width: 800px; /* 根据需要调整图片大小 */
  height: auto; /* 保持图片比例 */
  margin-top: 15px; /* 图片与文字的间距 */
  border-radius: 8px; /* 圆角效果 */
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* 添加阴影 */
  transition: transform 0.3s ease; /* 悬停动画 */
}

.main-view-image:hover {
  transform: scale(1.05); /* 悬停时放大 */
}
</style>