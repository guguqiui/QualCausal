<template>
  <div class="login-container">
    <div class="header-container">
      <div class="title-section">
        <img src="@/assets/logo.jpg" alt="Logo" class="logo-image" />
        <h1 class="title">Interactive Visual Analytics of Causality in Psychological Construct</h1>
      </div>
      <p class="intro-text">
        ✨ Welcome to our automated visualization system for psychological qualitative data.<br>
        To enhance your analytical process, we present an interactive system that illuminates causal relationships within qualitative data.
        Through network analysis and interactive visualization, our system transforms qualitative data into interpretable visual patterns that reveal underlying causal mechanisms.
      </p>
    </div>
    <h3>Please enter your User ID</h3>
    <input v-model="userId" placeholder="Enter user ID" />
    <button @click="login">Login</button>
    <img 
      src="@/assets/main-view-image.jpg" 
      alt="Main View Illustration"
      class="main-view-image"
    />
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>
<script>
import axios from 'axios';
import config from '@/config'; // 假设里面有 baseURL

export default {
  name: 'UserLogin',
  data() {
    return {
      userId: '',
      error: ''
    };
  },
  methods: {
    async login() {
      if (!this.userId) {
        this.error = "User ID cannot be empty";
        return;
      }
      try {
        const response = await axios.get(`${config.baseURL}/api/users/validate/${this.userId}`);
        if (response.data.valid) {
          this.$router.push({
            name: 'UploadView', 
            query: { userId: this.userId } 
          });
        } else {
          this.error = "Invalid User ID, please try again.";
        }
      } catch (err) {
        console.error(err);
        this.error = "Error checking userId, please try again later.";
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
  text-align: center;
}

.header-container {
  background-color: #E7F2F8; 
  padding: 20px;
  width: 100%;
  text-align: center;
}

.title-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-bottom: 20px;
}

.logo-image {
  max-height: 60px;
}

.title {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.intro-text {
  width: 1000px;
  font-size: 20px;
  line-height: 1.8;
  margin: 0 auto 20px auto; /* 让它水平居中 */
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}


.login-container input {
  padding: 8px;
  font-size: 16px;
  margin-top: 20px;
  margin-bottom: 30px;
  width: 80%;
  max-width: 300px;
  text-align: center;
}

.login-container button {
  padding: 8px 12px;
  font-size: 16px;
  cursor: pointer;
  border: none;
  background-color: #007bff;
  color: white;
  border-radius: 5px;
  transition: background-color 0.3s ease;
  max-width: 100px; /* 限制最大宽度 */
}

.login-container button:hover {
  background-color: #0056b3;
}

.error-message {
  color: red;
  margin-top: 10px;
}

.main-view-image {
  width: 600px; /* 根据需要调整图片大小 */
  height: auto; /* 保持图片比例 */
  margin-top: 15px; /* 图片与文字的间距 */
  border-radius: 8px; /* 圆角效果 */
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* 添加阴影 */
  transition: transform 0.3s ease; /* 悬停动画 */
}
</style>